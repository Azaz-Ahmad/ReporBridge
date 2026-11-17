from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app import db
from app.agent import graph
from app.fhir import validate_import
from app.rules import PATHS, PRE, PREG, RULES, code_matches, matches, observation, seed_records


def now():
    return datetime.now(UTC).isoformat()


def rows(connection, table, *conditions):
    return [dict(row) for row in connection.execute(select(table).where(*conditions)).mappings()]


def find(connection, table, identifier, required=False):
    row = connection.execute(select(table).where(table.c.id == identifier)).mappings().first()
    if row is None and required:
        raise HTTPException(404, f"{table.name} record not found")
    return dict(row) if row is not None else None


def ref(record):
    return f"{record['resourceType']}/{record['id']}"


def audit(connection, actor, action, patient_id, obligation=None, refs=(), **detail):
    connection.execute(db.audit.insert().values(
        recorded=now(), actor=actor, action=action, patient_id=patient_id,
        obligation_id=obligation["id"] if obligation else None,
        rule_key=obligation["rule_key"] if obligation else "", evidence_refs=list(refs), detail=detail,
    ))


def import_records(connection, actor, resources):
    validated = [(resource, validate_import(resource)) for resource in resources]
    for resource, patient_id in sorted(validated, key=lambda item: item[0]["resourceType"] != "Patient"):
        identifier = resource["id"]
        if resource["resourceType"] == "Patient":
            table = db.patients
            fields = {"stage": "preconception"}
        else:
            table = db.evidence
            fields = {"patient_id": patient_id}
            find(connection, db.patients, patient_id, required=True)
        existing = find(connection, table, identifier)
        if existing:
            if existing["resource"] != resource:
                raise HTTPException(409, f"Immutable resource {identifier} already exists with different content")
            continue
        connection.execute(table.insert().values(id=identifier, resource=resource, **fields))
        audit(connection, actor, "resource_imported", patient_id, refs=[ref(resource)])
    return sorted({patient_id for _, patient_id in validated})


def seed(connection, actor):
    patient_id, = import_records(connection, actor, seed_records())
    evaluate(connection, actor, patient_id)
    return patient_id


def evidence_for(connection, patient_id):
    return [row["resource"] for row in rows(connection, db.evidence, db.evidence.c.patient_id == patient_id)]


def evaluate(connection, actor, patient_id):
    patient = find(connection, db.patients, patient_id, required=True)
    records = evidence_for(connection, patient_id)
    existing = rows(connection, db.obligations, db.obligations.c.patient_id == patient_id)
    for rule_key, rule in RULES.items():
        if rule_key == PREG and patient["stage"] != "pregnancy":
            continue
        if rule_key == PRE and patient["stage"] != "preconception":
            continue
        candidates = [r for r in records if code_matches(r, rule["trigger"])]
        if not candidates or any(not matches(r, rule["trigger"], rule["value"]) for r in candidates):
            audit(connection, actor, "rule_abstained", patient_id, refs=[ref(r) for r in candidates],
                  evaluated_rule=rule_key, reason="missing or conflicting trigger evidence")
            continue
        if any(item["rule_key"] == rule_key for item in existing):
            continue
        if not find(connection, db.pathways, rule["pathway"]):
            connection.execute(db.pathways.insert().values(id=rule["pathway"], label=PATHS[rule["pathway"]]))
        if not find(connection, db.rules, rule_key):
            rule_id, version = rule_key.split("@")
            connection.execute(db.rules.insert().values(id=rule_key, rule_id=rule_id, version=version,
                                                       pathway_id=rule["pathway"], definition=rule))
        source = min(candidates, key=lambda record: record["id"])
        obligation = dict(id=uuid4().hex, patient_id=patient_id, rule_key=rule_key, source_id=source["id"],
                          owner="Demo care coordination", status="open", created=now())
        connection.execute(db.obligations.insert().values(**obligation))
        audit(connection, actor, "obligation_created", patient_id, obligation, [ref(source)])
        if rule_key == PREG:
            for prior in existing:
                if prior["rule_key"] == PRE and prior["status"] != "closed":
                    connection.execute(db.dependencies.insert().values(
                        id=uuid4().hex, obligation_id=obligation["id"], depends_on=prior["id"], rule_key=PREG))
                    audit(connection, actor, "dependency_linked", patient_id, obligation,
                          [ref(source), ref(find(connection, db.evidence, prior["source_id"])["resource"])],
                          depends_on=prior["id"])
        existing.append(obligation)
    return existing


def register_pregnancy(connection, actor, patient_id):
    patient = find(connection, db.patients, patient_id, required=True)
    if patient["stage"] == "pregnancy":
        return
    evaluate(connection, actor, patient_id)
    observation_id = f"{patient_id}-pregnancy" if len(patient_id) <= 54 else f"demo-{uuid4().hex}-pregnancy"
    resource = observation(patient_id, observation_id, "pregnancy-registration", "registered")
    import_records(connection, actor, [resource])
    connection.execute(db.events.insert().values(id=uuid4().hex, patient_id=patient_id,
                                                stage="pregnancy", recorded=now(), evidence_id=observation_id))
    connection.execute(db.patients.update().where(db.patients.c.id == patient_id).values(stage="pregnancy"))
    audit(connection, actor, "pregnancy_registered", patient_id, refs=[ref(resource)])
    for item in rows(connection, db.obligations, db.obligations.c.patient_id == patient_id):
        if item["status"] != "closed":
            source = find(connection, db.evidence, item["source_id"])["resource"]
            audit(connection, actor, "obligation_retained_at_transition", patient_id, item, [ref(source), ref(resource)])
    evaluate(connection, actor, patient_id)


def closure_candidates(connection, obligation):
    rule = find(connection, db.rules, obligation["rule_key"], required=True)["definition"]
    return [r for r in evidence_for(connection, obligation["patient_id"]) if code_matches(r, rule["closure"])]


def execute_agent(connection, actor, obligation_id):
    obligation = find(connection, db.obligations, obligation_id, required=True)
    if obligation["status"] == "closed":
        raise HTTPException(409, "Obligation already closed")
    pending = rows(connection, db.tasks, db.tasks.c.obligation_id == obligation_id, db.tasks.c.status == "pending")
    if pending:
        return pending[0]
    rule = find(connection, db.rules, obligation["rule_key"])["definition"]
    source = find(connection, db.evidence, obligation["source_id"])["resource"]
    result = graph.invoke({"authorized_records": [source, *closure_candidates(connection, obligation)],
                           "closure_code": rule["closure"], "source_ref": ref(source)})
    result = {field: result[field] for field in ("evidence_refs", "finding", "action", "route")}
    execution_id = uuid4().hex
    connection.execute(db.executions.insert().values(id=execution_id, obligation_id=obligation_id,
                                                    actor=actor, recorded=now(), result=result))
    task = dict(id=uuid4().hex, obligation_id=obligation_id, execution_id=execution_id,
                status="pending", action=result["action"])
    connection.execute(db.tasks.insert().values(**task))
    audit(connection, actor, "agent_routed_for_review", obligation["patient_id"], obligation,
          result["evidence_refs"], execution_id=execution_id, task_id=task["id"])
    return task


def review(connection, actor, task_id, decision, note, expected_evidence_refs):
    task = find(connection, db.tasks, task_id, required=True)
    obligation = find(connection, db.obligations, task["obligation_id"], required=True)
    if task["status"] != "pending" or obligation["status"] == "closed":
        raise HTTPException(409, "Review is no longer pending")
    candidates = closure_candidates(connection, obligation)
    evidence_refs = sorted(ref(resource) for resource in candidates)
    if evidence_refs != sorted(expected_evidence_refs):
        raise HTTPException(409, "Completion evidence changed. Refresh and review the current records.")
    approval = dict(id=uuid4().hex, task_id=task_id, obligation_id=obligation["id"], decision=decision,
                    actor=actor, recorded=now(), evidence_refs=evidence_refs, note=note)
    connection.execute(db.approvals.insert().values(**approval))
    connection.execute(db.tasks.update().where(db.tasks.c.id == task_id).values(status=decision))
    audit(connection, actor, f"review_{decision}", obligation["patient_id"], obligation, evidence_refs, task_id=task_id)
    return approval


def close(connection, actor, obligation_id):
    obligation = find(connection, db.obligations, obligation_id, required=True)
    if obligation["status"] == "closed":
        return {"status": "closed"}
    candidates = closure_candidates(connection, obligation)
    refs = sorted(ref(resource) for resource in candidates)
    rule = find(connection, db.rules, obligation["rule_key"])["definition"]
    reviews = rows(connection, db.approvals, db.approvals.c.obligation_id == obligation_id)
    latest = max(reviews, key=lambda review: review["recorded"], default=None)
    depends = rows(connection, db.dependencies, db.dependencies.c.obligation_id == obligation_id)
    if not candidates:
        reason = "Required completion evidence is missing."
    elif any(not matches(resource, rule["closure"], "verified") for resource in candidates):
        reason = "Completion records conflict or lack final verification."
    elif any(find(connection, db.obligations, edge["depends_on"])["status"] != "closed" for edge in depends):
        reason = "A linked preconception obligation remains open."
    elif not latest or latest["decision"] != "approve" or latest["evidence_refs"] != refs:
        reason = "Reviewer approval covering the current evidence is required."
    else:
        reason = ""
    if reason:
        audit(connection, actor, "closure_blocked", obligation["patient_id"], obligation, refs, reason=reason)
        return {"status": "blocked", "reason": reason}
    for resource in candidates:
        connection.execute(db.closures.insert().values(id=uuid4().hex, obligation_id=obligation_id,
                           evidence_id=resource["id"], approval_id=latest["id"], recorded=now()))
    connection.execute(db.obligations.update().where(db.obligations.c.id == obligation_id).values(status="closed"))
    audit(connection, actor, "closure_verified", obligation["patient_id"], obligation, refs, approval=latest["id"])
    return {"status": "closed"}


def snapshot(connection):
    tables = (db.patients, db.evidence, db.events, db.rules, db.obligations, db.dependencies,
              db.executions, db.tasks, db.approvals, db.closures)
    result = {table.name: rows(connection, table) for table in tables}
    result[db.audit.name] = [dict(row) for row in connection.execute(
        select(db.audit).order_by(db.audit.c.sequence.desc())).mappings()]
    return result
