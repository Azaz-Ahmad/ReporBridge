"""Scoped reset for the canonical Amira fixture."""

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select

from app import db, service
from app.rules import PRE, PREG, RULES, observation, seed_records
from app.prevention import service as prevention


def archive_summaries(connection):
    table = db.demo_archive
    query = select(table.c.id, table.c.patient_id, table.c.recorded, table.c.actor, table.c.audit_count)
    return [dict(row) for row in connection.execute(query.order_by(table.c.recorded.desc())).mappings()]


def reset_amira(connection, actor):
    seed_patient, initial = seed_records()
    patient_id = seed_patient["id"]
    patient = service.find(connection, db.patients, patient_id, required=True)
    if patient["resource"] != seed_patient or patient["stage"] not in {"preconception", "pregnancy"}:
        raise HTTPException(409, "Reset applies only to the canonical Amira fixture.")

    from app import historical_candidates
    candidate_allowlist = historical_candidates.reset_allowlist(connection, patient_id)
    obligations = service.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id)
    if any(item["rule_key"] not in {PRE, PREG} and item["id"] not in candidate_allowlist for item in obligations):
        raise HTTPException(409, "Amira has obligations outside the reset fixture.")
    ids = [item["id"] for item in obligations]
    events = service.rows(connection, db.events, db.events.c.patient_id == patient_id)
    allowed = {initial["id"]: initial}
    if any(event["stage"] == "pregnancy" and event["evidence_id"] == f"{patient_id}-pregnancy" for event in events):
        pregnancy = observation(patient_id, f"{patient_id}-pregnancy", "pregnancy-registration", "registered")
        allowed[pregnancy["id"]] = pregnancy
    for item in obligations:
        candidate = candidate_allowlist.get(item["id"])
        if candidate:
            configured = service.find(connection, db.rules, item["rule_key"], required=True)["definition"]
            expected = {key:value for key,value in candidate["rule_snapshot"]["lifecycle_rule"].items() if key!="id"}
            if configured != expected or candidate["confirmation_resource"] is None:
                raise HTTPException(409, "Candidate lifecycle attestation differs; records were preserved.")
            allowed[candidate["confirmation_resource"]["id"]] = candidate["confirmation_resource"]
        code = (candidate["rule_snapshot"]["lifecycle_rule"] if candidate else RULES[item["rule_key"]])["closure"]
        for scenario, value in (("verified", "verified"), ("conflicting", "unresolved")):
            identifier = f"demo-{item['id']}-{scenario}"
            allowed[identifier] = observation(patient_id, identifier, code, value)

    evidence = service.rows(connection, db.evidence, db.evidence.c.patient_id == patient_id)
    _, legacy_initial = seed_records(legacy=True)
    from app.prevention.tsp_demo import allowed_completion
    for row in evidence:
        if allowed_completion(connection, row["resource"]):
            allowed[row["id"]] = row["resource"]
    if any(allowed.get(row["id"]) != row["resource"] and row["resource"] != legacy_initial for row in evidence):
        raise HTTPException(409, "Amira has imported evidence outside the reset fixture. Her records were preserved.")

    edges = service.rows(connection, db.dependencies, or_(
        db.dependencies.c.obligation_id.in_(ids), db.dependencies.c.depends_on.in_(ids)))
    if any(edge["obligation_id"] not in ids or edge["depends_on"] not in ids for edge in edges):
        raise HTTPException(409, "Amira has dependencies outside the reset fixture.")
    related = [
        (table, table.c.obligation_id.in_(ids))
        for table in (db.closures, db.approvals, db.tasks, db.executions, db.dependencies)
    ]
    related_rows = {table.name: service.rows(connection, table, condition) for table, condition in related}
    audit_filter = db.audit.c.patient_id == patient_id
    audit_events = sorted(service.rows(connection, db.audit, audit_filter), key=lambda row: row["sequence"])
    already_ready = (
        patient["stage"] == "preconception" and len(events) == 1 and events[0]["stage"] == "preconception"
        and len(obligations) == 1 and obligations[0]["rule_key"] == PRE and obligations[0]["status"] == "open"
        and obligations[0]["source_id"] == initial["id"]
        and [row["resource"] for row in evidence] == [initial]
        and not any(related_rows.values())
        and all(event["action"] in {"resource_imported", "obligation_created", "demo_reset"} for event in audit_events)
        and prevention.initial_fixture(connection)
    )
    if already_ready:
        return {"status": "ready", "patient_id": patient_id, "archive_id": None}

    prevention.archive_for_reset(connection, actor)
    archive_id = uuid4().hex
    candidate_archive = historical_candidates.archive_for_reset(connection, patient_id)
    archived = {
        "historical_obligation_candidates": candidate_archive, **related_rows, db.patients.name: [patient], db.obligations.name: obligations,
        db.events.name: events, db.evidence.name: evidence, db.audit.name: audit_events,
    }
    connection.execute(db.demo_archive.insert().values(
        id=archive_id, patient_id=patient_id, recorded=service.now(), actor=actor,
        audit_count=len(audit_events), records=archived))

    for table, condition in [
        (db.audit, audit_filter), *related, (db.obligations, db.obligations.c.patient_id == patient_id),
        (db.events, db.events.c.patient_id == patient_id), (db.evidence, db.evidence.c.patient_id == patient_id),
        (db.patients, db.patients.c.id == patient_id),
    ]:
        connection.execute(table.delete().where(condition))
    service.seed(connection, actor)
    service.audit(connection, actor, "demo_reset", patient_id, refs=[f"Patient/{patient_id}"], archive_id=archive_id)
    return {"status": "reset", "patient_id": patient_id, "archive_id": archive_id}
