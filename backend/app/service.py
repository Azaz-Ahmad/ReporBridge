import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app import db
from app.agent import graph
from app.clinical.access import authorize, provision
from app.clinical.events import workflow_corrections
from app.fhir import check_references, validate_import
from app.rules import DEPENDENCY_RULES, PATHS, PRE, PREG, RULES, RULE_PRESENTATION, code_matches, matches, observation, seed_records

logger = logging.getLogger(__name__)


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
    for patient_id in {patient_id for _, patient_id in validated}:
        records = [resource for resource, subject in validated if subject == patient_id]
        existing_patient = find(connection, db.patients, patient_id)
        if not existing_patient and not any(record["resourceType"] == "Patient" for record in records):
            raise HTTPException(404, "Patient record not found.")
        if existing_patient:
            authorize(connection, actor, patient_id)
            records.extend([existing_patient["resource"], *evidence_for(connection, patient_id)])
        check_references(records)

    new_records = {}
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
        if table is db.patients:
            provision(connection, patient_id)
            connection.execute(db.events.insert().values(
                id=uuid4().hex, patient_id=patient_id, stage="preconception", recorded=now()))
        else:
            new_records.setdefault(patient_id, []).append(resource)
    for patient_id, imported in new_records.items():
        reconsider_closures(connection, actor, patient_id, imported)
    return sorted({patient_id for _, patient_id in validated})


def seed(connection, actor):
    patient, initial = seed_records()
    existing = find(connection, db.evidence, initial["id"])
    _, legacy_initial = seed_records(legacy=True)
    if existing and existing["resource"] == legacy_initial:
        initial = legacy_initial
    patient_id, = import_records(connection, actor, [patient, initial])
    evaluate(connection, actor, patient_id)
    return patient_id


def clinical_presentation(connection, obligation):
    patient, assessment = seed_records()
    if obligation["patient_id"] != patient["id"]:
        return {}
    subject = find(connection, db.patients, patient["id"], required=True)
    if subject["resource"] != patient:
        return {}
    source = find(connection, db.evidence, obligation["source_id"], required=True)["resource"]
    rule_key = obligation["rule_key"]
    if rule_key == PRE and source in (assessment, seed_records(legacy=True)[1]):
        return RULE_PRESENTATION[PRE]
    if rule_key == PREG and source == observation(patient["id"], "demo-amira-pregnancy", "pregnancy-registration", "registered"):
        return RULE_PRESENTATION[PREG]
    return {}


def evidence_for(connection, patient_id):
    return [row["resource"] for row in rows(connection, db.evidence, db.evidence.c.patient_id == patient_id)]


def decision_evidence_for(connection, patient_id):
    corrections = workflow_corrections(connection, patient_id)
    return [{**record, "status": "entered-in-error"} if record["id"] in corrections else record
            for record in evidence_for(connection, patient_id)]


def link_dependency(connection, actor, obligation, prior, kind):
    expected = DEPENDENCY_RULES.get(obligation["rule_key"])
    if (obligation["id"] == prior["id"] or obligation["patient_id"] != prior["patient_id"]
            or expected != (prior["rule_key"], kind)):
        raise HTTPException(409, "Dependency is incompatible with the configured rule.")
    pending = [prior["id"]]
    visited = set()
    while pending:
        identifier = pending.pop()
        if identifier == obligation["id"]:
            raise HTTPException(409, "Dependency would create a cycle.")
        if identifier not in visited:
            visited.add(identifier)
            pending.extend(edge["depends_on"] for edge in rows(
                connection, db.dependencies, db.dependencies.c.obligation_id == identifier))
    matching = rows(connection, db.dependencies, db.dependencies.c.obligation_id == obligation["id"],
                    db.dependencies.c.depends_on == prior["id"])
    if matching:
        return
    connection.execute(db.dependencies.insert().values(
        id=uuid4().hex, obligation_id=obligation["id"], depends_on=prior["id"],
        rule_key=obligation["rule_key"], kind=kind))
    sources = [ref(find(connection, db.evidence, item["source_id"], required=True)["resource"])
               for item in (obligation, prior)]
    audit(connection, actor, "dependency_linked", obligation["patient_id"], obligation, sources,
          depends_on=prior["id"], kind=kind)


def prerequisite_blocked(connection, obligation, visited=()):
    identifier = obligation["id"]
    if identifier in visited:
        return True
    config = DEPENDENCY_RULES.get(obligation["rule_key"])
    edges = rows(connection, db.dependencies, db.dependencies.c.obligation_id == identifier)
    if not config:
        return bool(edges)
    expected = rows(connection, db.obligations, db.obligations.c.patient_id == obligation["patient_id"],
                    db.obligations.c.rule_key == config[0])
    if {edge["depends_on"] for edge in edges} != {prior["id"] for prior in expected}:
        return True
    if any(edge["rule_key"] != obligation["rule_key"] or edge["kind"] != config[1] for edge in edges):
        return True
    return any(prior["status"] != "closed" or prerequisite_blocked(connection, prior, (*visited, identifier))
               for prior in expected)


def qualifying_source(connection, obligation, rule):
    records = [resource for resource in decision_evidence_for(connection, obligation["patient_id"])
               if code_matches(resource, rule["trigger"])]
    return (any(resource["id"] == obligation["source_id"] for resource in records)
            and all(matches(resource, rule["trigger"], rule["value"]) for resource in records))


def reconsider_closures(connection, actor, patient_id, imported):
    closed = {item["id"]: item for item in rows(
        connection, db.obligations, db.obligations.c.patient_id == patient_id, db.obligations.c.status == "closed")}
    affected = []
    for item in closed.values():
        rule = find(connection, db.rules, item["rule_key"], required=True)["definition"]
        changed_completion = any(code_matches(record, rule["closure"]) for record in imported)
        changed_trigger = any(code_matches(record, rule["trigger"]) for record in imported)
        if changed_completion or (changed_trigger and not qualifying_source(connection, item, rule)):
            affected.append((item["id"], "New evidence requires reconciliation."))
    while affected:
        identifier, reason = affected.pop()
        item = closed.pop(identifier, None)
        if not item:
            continue
        connection.execute(db.obligations.update().where(db.obligations.c.id == identifier).values(status="open"))
        audit(connection, actor, "closure_reopened", patient_id, item, [ref(record) for record in imported],
              reason=reason)
        affected.extend((edge["obligation_id"], "A prerequisite obligation reopened.") for edge in rows(
            connection, db.dependencies, db.dependencies.c.depends_on == identifier))


def evaluate(connection, actor, patient_id):
    patient = find(connection, db.patients, patient_id, required=True)
    records = decision_evidence_for(connection, patient_id)
    existing = rows(connection, db.obligations, db.obligations.c.patient_id == patient_id)
    for rule_key, rule in RULES.items():
        if patient["stage"] != rule["pathway"]:
            continue
        configured = find(connection, db.rules, rule_key)
        if configured and configured["definition"] != rule:
            raise HTTPException(409, "A persisted rule version differs from the deployed definition.")
        candidates = [r for r in records if code_matches(r, rule["trigger"])]
        if not candidates or any(not matches(r, rule["trigger"], rule["value"]) for r in candidates):
            audit(connection, actor, "rule_abstained", patient_id, refs=[ref(r) for r in candidates],
                  evaluated_rule=rule_key, reason="missing or conflicting trigger evidence")
            continue
        if any(item["rule_key"] == rule_key for item in existing):
            continue
        if not find(connection, db.pathways, rule["pathway"]):
            connection.execute(db.pathways.insert().values(id=rule["pathway"], label=PATHS[rule["pathway"]]))
        if not configured:
            rule_id, version = rule_key.split("@")
            connection.execute(db.rules.insert().values(id=rule_key, rule_id=rule_id, version=version,
                                                       pathway_id=rule["pathway"], definition=rule))
        source = min(candidates, key=lambda record: record["id"])
        obligation = dict(id=uuid4().hex, patient_id=patient_id, rule_key=rule_key, source_id=source["id"],
                          owner="Demo care coordination", status="open", created=now())
        connection.execute(db.obligations.insert().values(**obligation))
        audit(connection, actor, "obligation_created", patient_id, obligation, [ref(source)])
        for prior in existing:
            configured_edge = DEPENDENCY_RULES.get(rule_key)
            if configured_edge and prior["rule_key"] == configured_edge[0]:
                link_dependency(connection, actor, obligation, prior, configured_edge[1])
        existing.append(obligation)
    return existing


def register_pregnancy(connection, actor, patient_id, session_id=None):
    patient = find(connection, db.patients, patient_id, required=True)
    if patient["stage"] == "pregnancy":
        from app.historical_candidates import evaluate as identify_candidates
        identify_candidates(connection, actor, patient_id, session_id)
        return
    if patient["stage"] != "preconception":
        raise HTTPException(409, "Pregnancy requires a preconception record.")
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
    from app.historical_candidates import evaluate as identify_candidates
    identify_candidates(connection, actor, patient_id, session_id)


def closure_candidates(connection, obligation):
    rule = find(connection, db.rules, obligation["rule_key"], required=True)["definition"]
    return [r for r in decision_evidence_for(connection, obligation["patient_id"]) if code_matches(r, rule["closure"])]


def authorized_records(connection, obligation):
    rule = find(connection, db.rules, obligation["rule_key"], required=True)["definition"]
    return [record for record in decision_evidence_for(connection, obligation["patient_id"])
            if record["id"] == obligation["source_id"] or code_matches(record, rule["trigger"])
            or code_matches(record, rule["closure"])]


def execution_refs(connection, obligation):
    return sorted(ref(record) for record in authorized_records(connection, obligation))


def closure_authorized(connection, obligation, approval, refs):
    if not approval or approval["decision"] != "approve" or approval["evidence_refs"] != refs:
        return False
    reopened = connection.execute(select(db.audit.c.recorded).where(
        db.audit.c.obligation_id == obligation["id"], db.audit.c.action == "closure_reopened"
    ).order_by(db.audit.c.sequence.desc()).limit(1)).scalar_one_or_none()
    if reopened and approval["recorded"] <= reopened:
        return False
    task = find(connection, db.tasks, approval["task_id"], required=True)
    execution = find(connection, db.executions, task["execution_id"], required=True)
    return (task["status"] == "approve" and task["obligation_id"] == obligation["id"]
            and execution["obligation_id"] == obligation["id"]
            and execution["result"]["finding"] == "evidence_available"
            and sorted(execution["result"]["evidence_refs"]) == execution_refs(connection, obligation))


def execute_agent(connection, actor, obligation_id):
    obligation = find(connection, db.obligations, obligation_id, required=True)
    if obligation["status"] == "closed":
        raise HTTPException(409, "Obligation already closed")
    pending = rows(connection, db.tasks, db.tasks.c.obligation_id == obligation_id, db.tasks.c.status == "pending")
    rule = find(connection, db.rules, obligation["rule_key"])["definition"]
    records = authorized_records(connection, obligation)
    current_refs = sorted(ref(record) for record in records)
    for previous in pending:
        execution = find(connection, db.executions, previous["execution_id"], required=True)
        if sorted(execution["result"]["evidence_refs"]) == current_refs:
            return previous
    try:
        narrative = clinical_presentation(connection, obligation)
        result = graph.invoke({"authorized_records": records, "closure_code": rule["closure"],
                               "proposal_context": narrative.get("next_action", rule["description"]),
                               "source_qualified": qualifying_source(connection, obligation, rule)})
        result = {field: result[field] for field in ("evidence_refs", "finding", "action", "route", "trace")}
    except Exception:
        logger.warning("Care-resolution graph failed for obligation %s", obligation_id)
        execution_id = uuid4().hex
        connection.execute(db.executions.insert().values(
            id=execution_id, obligation_id=obligation_id, actor=actor, recorded=now(),
            result={"evidence_refs": current_refs, "finding": "failed", "action": "Retry coordination.",
                    "route": "none"}))
        audit(connection, actor, "agent_execution_failed", obligation["patient_id"], obligation, current_refs,
              execution_id=execution_id)
        return {"status": "failed", "reason": "Coordination failed before review routing. Retry the run."}
    for previous in pending:
        connection.execute(db.tasks.update().where(db.tasks.c.id == previous["id"]).values(status="superseded"))
        audit(connection, actor, "proposal_superseded", obligation["patient_id"], obligation, current_refs,
              task_id=previous["id"])
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
    authorize(connection, actor, obligation["patient_id"])
    if task["status"] != "pending" or obligation["status"] == "closed":
        raise HTTPException(409, "Review is no longer pending")
    candidates = closure_candidates(connection, obligation)
    evidence_refs = sorted(ref(resource) for resource in candidates)
    if evidence_refs != sorted(expected_evidence_refs):
        raise HTTPException(409, "Completion evidence changed. Refresh and review the current records.")
    execution = find(connection, db.executions, task["execution_id"], required=True)
    if decision == "approve" and sorted(execution["result"]["evidence_refs"]) != execution_refs(connection, obligation):
        raise HTTPException(409, "Evidence changed since the agent proposal. Run coordination again before approving.")
    approval = dict(id=uuid4().hex, task_id=task_id, obligation_id=obligation["id"], decision=decision,
                    actor=actor, recorded=now(), evidence_refs=evidence_refs, note=note)
    connection.execute(db.approvals.insert().values(**approval))
    connection.execute(db.tasks.update().where(db.tasks.c.id == task_id).values(status=decision))
    audit(connection, actor, f"review_{decision}", obligation["patient_id"], obligation, evidence_refs, task_id=task_id)
    return approval


def assess_closure(connection, obligation):
    candidates = closure_candidates(connection, obligation)
    refs = sorted(ref(resource) for resource in candidates)
    rule = find(connection, db.rules, obligation["rule_key"])["definition"]
    reviews = rows(connection, db.approvals, db.approvals.c.obligation_id == obligation["id"])
    latest = max(reviews, key=lambda review: (review["recorded"], review["id"]), default=None)
    if not qualifying_source(connection, obligation, rule):
        reason = "Source evidence conflicts or no longer qualifies."
    elif not candidates:
        reason = "Required completion evidence is missing."
    elif any(not matches(resource, rule["closure"], "verified") for resource in candidates):
        reason = "Completion records conflict or lack final verification."
    elif prerequisite_blocked(connection, obligation):
        reason = "A linked preconception obligation remains open."
    elif not closure_authorized(connection, obligation, latest, refs):
        reason = "Reviewer approval covering the current evidence is required."
    else:
        reason = ""
    return reason, candidates, refs, latest


def close(connection, actor, obligation_id):
    obligation = find(connection, db.obligations, obligation_id, required=True)
    if obligation["status"] == "closed":
        return {"status": "closed"}
    reason, candidates, refs, latest = assess_closure(connection, obligation)
    if reason:
        audit(connection, actor, "closure_blocked", obligation["patient_id"], obligation, refs, reason=reason)
        return {"status": "blocked", "reason": reason}
    for resource in candidates:
        connection.execute(db.closures.insert().values(id=uuid4().hex, obligation_id=obligation_id,
                           evidence_id=resource["id"], approval_id=latest["id"], recorded=now()))
    connection.execute(db.obligations.update().where(db.obligations.c.id == obligation_id).values(status="closed"))
    audit(connection, actor, "closure_verified", obligation["patient_id"], obligation, refs, approval=latest["id"])
    return {"status": "closed"}


def snapshot(connection, patient_ids):
    result = {db.patients.name: rows(connection, db.patients, db.patients.c.id.in_(patient_ids)),
              db.rules.name: rows(connection, db.rules)}
    for table in (db.evidence, db.events, db.obligations):
        result[table.name] = rows(connection, table, table.c.patient_id.in_(patient_ids))
    ids = [item["id"] for item in result[db.obligations.name]]
    for table in (db.executions, db.tasks, db.approvals, db.closures):
        result[table.name] = rows(connection, table, table.c.obligation_id.in_(ids))
    result[db.dependencies.name] = rows(connection, db.dependencies, db.dependencies.c.obligation_id.in_(ids),
                                        db.dependencies.c.depends_on.in_(ids))
    result[db.audit.name] = [dict(row) for row in connection.execute(select(db.audit).where(
        db.audit.c.patient_id.in_(patient_ids)).order_by(db.audit.c.sequence.desc())).mappings()]
    return result
