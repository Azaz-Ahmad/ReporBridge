"""Read-only coordination projection. Never part of clinical calculation or model context."""
import json
from pathlib import Path
from app.clinical.access import permitted
from app.prevention import tsp

POLICY_FILE = Path(__file__).with_name("coordination_policy_v1.json")


def policy():
    return json.loads(POLICY_FILE.read_text(encoding="utf-8"))


def next_action(status, definition=None):
    definition = definition if definition is not None else policy()
    # Unknown states fail closed: no invented action or automatic routing.
    return dict(definition["actions"].get(status, {"action": None, "owner_role": None}))


def project(result):
    definition = policy()
    matching = (result["status"] == "NO_POLICY" or
                (result["policy_id"], result["policy_version"]) ==
                (definition["window_policy_id"], definition["window_policy_version"]))
    action = next_action(result["status"], definition) if matching else {"action": None, "owner_role": None}
    return {**result, "coordination": {**action, "policy_id": definition["id"],
            "policy_version": definition["version"], "scope": definition["scope"], "policy_matched": matching}}


def patient(connection, actor, patient_id, session_id=None):
    return project(tsp.patient_window(connection, actor, patient_id, session_id))


def queue(connection, actor, session_id=None):
    return [patient(connection, actor, identifier, session_id) for identifier in sorted(permitted(connection, actor))]


def traceability(connection, actor, patient_id, session_id=None):
    from sqlalchemy import select
    from app import db, history, service
    from app.clinical.access import authorize
    from app.clinical.contracts import Filters
    from app.clinical.gateway import ClinicalRetrieval
    from app.prevention.schema_v1 import policies

    context = authorize(connection, actor, patient_id)
    result = tsp.patient_window(connection, actor, patient_id, session_id)
    row = connection.execute(select(policies).where(policies.c.id == result["policy_id"],
        policies.c.version == result["policy_version"], policies.c.status == "active")).mappings().first()
    definition = row["definition"] if row else None
    text = policy()["eligibility_text"]
    criteria = []
    if definition:
        criteria = [text["registration"], text["dating"].format(**definition)]
        for window in definition["windows"]:
            if window.get("requires_carried_obligation"):
                criteria.append(text["carried"].format(**window))
            template = "registration_window" if window.get("start") == "pregnancy_registration" else "day_window"
            criteria.append(text[template].format(**window))
    historic = history.view(connection, actor, patient_id, session_id)
    historical_policy = history.policy()
    historical_rules = [{"rule_id": rule["id"],
        "criteria": text["historical"].format(**rule),
        "triggered": next((trace["triggered"] for trace in historic["rule_traces"] if trace["rule_id"] == rule["id"]), False)}
        for rule in historical_policy["rules"]
        if historical_policy["parent_policy_id"] == result["policy_id"]
        and historical_policy["parent_policy_version"] == result["policy_version"]]
    obligations = service.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id)
    logical_ids = {item["source_id"] for item in obligations if item["id"] in result["obligation_ids"]}
    evidence_ids = {item["source_id"] for item in [*result["inputs_used"], *result["completion_inputs"]]}
    evidence_ids.update(item["id"] for item in historic["findings"])
    retrieval = ClinicalRetrieval(connection, context)
    rows, *metadata = retrieval.prepare(Filters())
    evidence = []
    for source in rows:
        if source["id"] not in evidence_ids and source["resource_id"] not in logical_ids:
            continue
        item = retrieval.result(source, *metadata).model_dump(mode="json")
        if item["quality"]["state"] != "valid":
            continue
        evidence.append({key: item[key] for key in ("id", "kind", "version", "clinical_time", "digest", "provenance", "quality")} | {
            "label": source["resource"].get("description") or source["resource"].get("code", {}).get("text") or item["kind"],
            "source_url": "/api/v1/clinical/patients/" + patient_id + "/evidence/" + item["id"]})
    return {"patient_id": patient_id, "as_of": result["as_of"], "status": result["status"],
            "source_guideline": "pending clinical confirmation", "policy_id": result["policy_id"],
            "policy_version": result["policy_version"], "policy_active": bool(definition),
            "eligibility_criteria": criteria, "supporting_evidence": evidence,
            "historical_policy": {"id": historical_policy["id"], "version": historical_policy["version"], "rules": historical_rules}}
