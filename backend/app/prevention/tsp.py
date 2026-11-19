"""Trusted deterministic TSP projection over existing authorized evidence."""
from datetime import date, datetime, timedelta, timezone
import os
from sqlalchemy import select
from app import db, service as clinical
from app.clinical.access import authorize, permitted, fail
from app.clinical.contracts import Filters
from app.clinical.gateway import ClinicalRetrieval
from app.prevention.schema_v1 import policies
from app.prevention.tsp_schema import clocks
from app.prevention.window import calculate, resolve_dating
from app.rules import PRE

DEFAULT_AS_OF = date(2026, 11, 22)


def demo_enabled():
    return os.getenv("DEMO_MODE", "").lower() in {"1", "true", "yes"}


def clock(connection, session_id=None, new_date=None, reset=False):
    enabled = demo_enabled()
    if (new_date or reset) and not enabled:
        fail(403, "demo_disabled", "Demo clock is disabled.")
    value = connection.execute(select(clocks.c.as_of).where(clocks.c.session_id == session_id)).scalar_one_or_none() if session_id and enabled else None
    if enabled and session_id and (new_date or reset or not value):
        value = (DEFAULT_AS_OF if reset or not new_date else new_date).isoformat()
        connection.execute(clocks.delete().where(clocks.c.session_id == session_id))
        connection.execute(clocks.insert().values(session_id=session_id, as_of=value))
    today = datetime.now(timezone(timedelta(hours=4))).date()
    return {"demo_mode": enabled, "as_of": value or (DEFAULT_AS_OF.isoformat() if enabled else today.isoformat()),
            "timezone": "Asia/Dubai", "label": "DEMO CLOCK — synthetic dates" if enabled else "Asia/Dubai calendar date"}


def day(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.utcoffset() is None:
            raise ValueError("Source datetime requires a timezone")
        return moment.astimezone(timezone(timedelta(hours=4))).date()


def patient_window(connection, actor, patient_id, session_id=None, as_of=None):
    context = authorize(connection, actor, patient_id)
    current = clock(connection, session_id)
    projection_date = as_of or date.fromisoformat(current["as_of"])
    row = connection.execute(select(policies).where(policies.c.id == "glycemic-assessment-pregnancy")).mappings().first()
    policy = {**row["definition"], "id": row["id"], "version": row["version"]} if row and row["status"] == "active" else None
    retrieval = ClinicalRetrieval(connection, context)
    rows, *metadata = retrieval.prepare(Filters())
    sources = [{**retrieval.result(row, *metadata).model_dump(mode="json"), "resource": row["resource"]}
               for row in rows if row["id"] not in metadata[0]]
    dating = resolve_dating(policy, sources) if policy else {"due_date": None, "inputs": [], "missing_evidence": []}
    registrations = [item for item in sources if any(c.get("code") == "pregnancy-registration"
        for c in item["resource"].get("code", {}).get("coding", [])) and item["quality"]["state"] == "valid"]
    registered = None
    if registrations:
        try:
            registered = min(day(item["resource"].get("effectiveDateTime")) for item in registrations)
        except (ValueError, TypeError):
            pass
    missing = list(dating["missing_evidence"])
    if not registered:
        missing.append("Pregnancy registration date")
    obligations = clinical.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id,
                                db.obligations.c.rule_key == PRE)
    retained = clinical.rows(connection, db.audit, db.audit.c.patient_id == patient_id,
                             db.audit.c.action == "obligation_retained_at_transition")
    carried = any(item["status"] == "open" or any(event["obligation_id"] == item["id"] for event in retained) for item in obligations)
    completion_dates, completion_inputs = [], []
    for obligation in obligations:
        rule = clinical.find(connection, db.rules, obligation["rule_key"], required=True)["definition"]
        candidates = clinical.closure_candidates(connection, obligation)
        if (not clinical.qualifying_source(connection, obligation, rule) or not candidates
                or any(not clinical.matches(item, rule["closure"], "verified") for item in candidates)):
            continue
        for resource in candidates:
            source = next((item for item in sources if item["source"] == "workflow" and item["resource_id"] == resource["id"]), None)
            if not source or source["quality"]["state"] != "valid":
                continue
            try:
                completed_on = day(resource.get("effectiveDateTime"))
            except (ValueError, TypeError):
                completed_on = None
            if completed_on:
                completion_dates.append(completed_on)
                completion_inputs.append({"source_id": source["id"], "version": source["version"],
                    "digest": source["digest"], "evidence_date": completed_on.isoformat()})
    result = calculate(policy, due_date=dating["due_date"], registered_on=registered,
        as_of=projection_date, carried_obligation=carried, completion_dates=completion_dates, inputs=dating["inputs"], missing_evidence=missing)
    result.update(patient_id=patient_id, clock=current, dating_selection=dating.get("selection"),
                  obligation_ids=[item["id"] for item in obligations], completion_inputs=completion_inputs,
                  completion_verified=bool(obligations) and all(item["status"] == "closed" for item in obligations))
    return result


def queue(connection, actor, session_id=None):
    return [patient_window(connection, actor, patient, session_id) for patient in sorted(permitted(connection, actor))]
