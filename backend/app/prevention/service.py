"""Persisted decision workflow. Retrieval readiness never establishes clinical sufficiency."""
from uuid import uuid4

from sqlalchemy import select

from app import db, service as clinical
from app.service import rows
from app.clinical.access import authorize, fail, now, permitted
from app.clinical.contracts import Filters
from app.clinical.gateway import ClinicalRetrieval
from app.clinical.normalize import digest
from app.prevention import timing
from app.prevention.contracts import RULE
from app.prevention.schema_v1 import audit, decisions, policies, prerequisites, records
from app.rules import PRE

REGISTRY = (
    {"category": "Metabolic assessment observation", "kind": "Observation", "code": "metabolic-assessment"},
    {"category": "Assessment summary document", "kind": "DocumentReference", "document_type": "assessment-summary"},
)
TERMINAL = {"decided", "cancelled"}


def event(connection, decision, actor, action, **detail):
    connection.execute(audit.insert().values(decision_id=decision["id"], patient_id=decision["patient_id"],
        actor=actor, action=action, recorded=now(), detail=detail))


def get(connection, actor, identifier, active=True):
    row = connection.execute(select(decisions).where(decisions.c.id == identifier)).mappings().first()
    if not row:
        fail(404, "decision_unavailable", "Decision unavailable in this scope.")
    authorize(connection, actor, row["patient_id"])
    if active and row["archived"]:
        fail(409, "decision_archived", "This decision belongs to an archived demonstration.")
    return dict(row)


def policy_for(connection, identifier):
    if not identifier:
        return None
    row = connection.execute(select(policies).where(policies.c.id == identifier)).mappings().first()
    return dict(row) if row else None


def catalog(connection, patient_id):
    scope = authorize(connection, "coordinator", patient_id)
    retrieval = ClinicalRetrieval(connection, scope)
    page = retrieval.prepare(Filters())
    return [retrieval.result(row, *page[1:]).model_dump(mode="json") for row in page[0]]


def matches(item, definition):
    if item["kind"] != definition["kind"]:
        return False
    if "code" in definition:
        return any(code["code"] == definition["code"] for code in item["normalized"].get("codings", []))
    return item["normalized"].get("document", {}).get("type") == definition["document_type"]


def evaluate(connection, decision, actor="system"):
    if decision["archived"]:
        return decision
    evidence = catalog(connection, decision["patient_id"])
    required = rows(connection, prerequisites, prerequisites.c.decision_id == decision["id"])
    evaluated = []
    for prerequisite in required:
        candidates = [item for item in evidence if matches(item, prerequisite["definition"])]
        states = {item["quality"]["state"] for item in candidates}
        if not candidates:
            status = "missing"
        elif "conflicting" in states:
            status = "conflicting"
        elif states <= {"unavailable"}:
            status = "unavailable"
        elif states - {"valid"}:
            status = "requires_reconciliation"
        else:
            status = "available_for_review"
        evaluated.append({"id": prerequisite["id"], "category": prerequisite["category"], "status": status,
                          "source_refs": sorted(item["id"] for item in candidates),
                          "issues": sorted({warning for item in candidates for warning in item["quality"]["warnings"]}),
                          "definition": prerequisite["definition"], "rule_key": prerequisite["rule_key"]})
    obligation = clinical.find(connection, db.obligations, decision["obligation_id"], required=True)
    policy = policy_for(connection, decision["policy_id"])
    stage_events = rows(connection, db.events, db.events.c.patient_id == decision["patient_id"])
    snapshot = {"evidence": [{"id": item["id"], "version": item["version"], "digest": item["digest"],
                              "quality": item["quality"], "values": item["normalized"].get("values", {}),
                              "citation": item["citation"], "clinical_time": item["clinical_time"]} for item in evidence],
                "prerequisites": evaluated, "obligation_status": obligation["status"],
                "life_stage_events": sorted((item["id"], item["stage"], item["recorded"]) for item in stage_events),
                "policy": policy, "owner": decision["owner"], "rule_key": decision["rule_key"]}
    fingerprint = digest(snapshot)
    if fingerprint == decision["snapshot_hash"]:
        return decision
    stamp = now()
    for item in evaluated:
        connection.execute(prerequisites.update().where(prerequisites.c.id == item["id"]).values(
            status=item["status"], source_refs=item["source_refs"], issues=item["issues"], evaluated=stamp))
    state = decision["status"]
    ready = all(item["status"] == "available_for_review" for item in evaluated)
    if state in {"awaiting_evidence", "ready_for_review", "under_review"}:
        state = "ready_for_review" if ready else "awaiting_evidence"
    previous = decision["snapshot"]
    connection.execute(decisions.update().where(decisions.c.id == decision["id"]).values(
        snapshot=snapshot, snapshot_hash=fingerprint, revision=decision["revision"] + 1,
        status=state, updated=stamp, due_date=timing.evaluate(policy)["due_at"]))
    event(connection, decision, actor, "prerequisites_evaluated", readiness=state,
          source_refs=sorted({ref for item in evaluated for ref in item["source_refs"]}),
          timing=timing.evaluate(policy), snapshot=fingerprint)
    if previous.get("obligation_status") != "closed" and obligation["status"] == "closed":
        event(connection, decision, actor, "obligation_verified_closed", obligation_id=obligation["id"])
    if previous and previous.get("life_stage_events") != snapshot["life_stage_events"]:
        event(connection, decision, actor, "life_stage_observed", events=snapshot["life_stage_events"])
    if state == "decided" and previous:
        event(connection, decision, actor, "evidence_changed_after_decision", snapshot=fingerprint)
    return get(connection, "coordinator", decision["id"])


def create(connection, actor, request, purpose="manual"):
    obligation = clinical.find(connection, db.obligations, request.obligation_id, required=True)
    authorize(connection, actor, obligation["patient_id"])
    if obligation["rule_key"] != PRE:
        fail(409, "unsupported_readiness_rule", "The illustrative metabolic registry applies to preconception review obligations.")
    if request.policy_id and not (policy := policy_for(connection, request.policy_id)):
        fail(404, "policy_unavailable", "Timing policy unavailable.")
    if request.policy_id and policy["status"] != "active":
        fail(409, "inactive_policy", "Choose an active timing policy.")
    stamp = now()
    decision = dict(id="decision-" + uuid4().hex, patient_id=obligation["patient_id"],
        obligation_id=obligation["id"], purpose=purpose, rationale=request.rationale, owner=request.owner,
        rule_key=RULE, status="awaiting_evidence", policy_id=request.policy_id, due_date=None,
        source_refs=[item["id"] for item in catalog(connection, obligation["patient_id"])
                     if item["resource_id"] == obligation["source_id"] and item["source"] == "workflow"], snapshot={}, snapshot_hash="", revision=0,
        archived=False, created=stamp, updated=stamp, last_investigation_id=None)
    connection.execute(decisions.insert().values(**decision))
    for definition in REGISTRY:
        connection.execute(prerequisites.insert().values(id=uuid4().hex, decision_id=decision["id"],
            category=definition["category"], rule_key=RULE, definition=definition,
            status="missing", source_refs=[], issues=[], evaluated=stamp))
    event(connection, decision, actor, "decision_created", owner=request.owner,
          rationale=request.rationale, obligation_id=obligation["id"], rule_key=RULE)
    evaluate(connection, decision, actor)
    return view(connection, get(connection, actor, decision["id"]))


def ensure_amira(connection):
    from app.prevention.contracts import CreateDecision
    if not clinical.find(connection, db.patients, "demo-amira"):
        return
    linked = rows(connection, db.obligations, db.obligations.c.patient_id == "demo-amira", db.obligations.c.rule_key == PRE)
    if not linked or not clinical.clinical_presentation(connection, linked[0]):
        return
    if rows(connection, decisions, decisions.c.patient_id == "demo-amira", decisions.c.purpose == "amira-fixture",
            decisions.c.archived.is_(False)):
        return
    create(connection, "coordinator", CreateDecision(obligation_id=linked[0]["id"],
        owner="Synthetic reproductive care review team",
        rationale="Review preconception metabolic assessment documentation and record clinician reconciliation or follow-up."),
        purpose="amira-fixture")


def synchronize(connection):
    ensure_amira(connection)
    for decision in rows(connection, decisions, decisions.c.archived.is_(False)):
        evaluate(connection, decision)


def view(connection, decision):
    policy = policy_for(connection, decision["policy_id"])
    recorded = rows(connection, records, records.c.decision_id == decision["id"])
    outcome = recorded[0] if recorded else None
    return {**decision, "timing": timing.evaluate(policy), "timing_policy": policy,
            "prerequisites": rows(connection, prerequisites, prerequisites.c.decision_id == decision["id"]),
            "record": outcome,
            "record_snapshot_current": not outcome or digest(outcome["snapshot"]) == digest(decision["snapshot"])}


def snapshot(connection, actor, patient_id=None):
    synchronize(connection)
    patients = permitted(connection, actor)
    if patient_id:
        authorize(connection, actor, patient_id)
        patients = {patient_id}
    items = rows(connection, decisions, decisions.c.patient_id.in_(patients))
    visible = [view(connection, item) for item in items]
    active = [item for item in visible if not item["archived"] and item["status"] not in TERMINAL]
    counts = {"awaiting_evidence": sum(item["status"] == "awaiting_evidence" for item in active),
              "ready_for_review": sum(item["status"] == "ready_for_review" for item in active),
              "due_soon": sum(item["timing"]["state"] == "due_soon" for item in active),
              "overdue": sum(item["timing"]["state"] == "overdue" for item in active)}
    history = rows(connection, audit, audit.c.patient_id.in_(patients))
    return {"decisions": visible, "counts": counts, "history": sorted(history, key=lambda item: item["sequence"]),
            "as_of": now(), "synthetic_only": True}


def current(connection, actor, identifier, revision):
    decision = evaluate(connection, get(connection, actor, identifier))
    if decision["revision"] != revision:
        fail(409, "stale_decision", "Decision evidence or policy changed. Refresh before continuing.")
    return decision


def transition(connection, actor, identifier, request):
    decision = current(connection, actor, identifier, request.revision)
    if request.action == "begin_review":
        if actor != "reviewer":
            fail(403, "reviewer_required", "A clinical reviewer must begin review.")
        allowed = {"awaiting_evidence", "ready_for_review", "escalated"}
        target = "under_review"
    elif request.action == "resume":
        allowed = {"escalated"}
        target = "ready_for_review" if all(item["status"] == "available_for_review" for item in
            rows(connection, prerequisites, prerequisites.c.decision_id == identifier)) else "awaiting_evidence"
    else:
        allowed = {"awaiting_evidence", "ready_for_review", "under_review", "escalated"}
        target = "escalated" if request.action == "escalate" else "cancelled"
    if decision["status"] not in allowed:
        fail(409, "invalid_transition", "This decision cannot take the requested transition.")
    connection.execute(decisions.update().where(decisions.c.id == identifier).values(
        status=target, revision=decision["revision"] + 1, updated=now()))
    event(connection, decision, actor, "review_started" if target == "under_review" else "decision_" + target,
          from_status=decision["status"], to_status=target, rationale=request.rationale,
          snapshot=decision["snapshot_hash"])
    return view(connection, get(connection, actor, identifier))


def record(connection, actor, identifier, request):
    if actor != "reviewer":
        fail(403, "reviewer_required", "Only a clinical reviewer may record a decision.")
    decision = current(connection, actor, identifier, request.revision)
    if decision["status"] != "under_review" or request.reviewed_snapshot != decision["snapshot_hash"]:
        fail(409, "review_required", "Review the current evidence snapshot before recording a decision.")
    if request.outcome == "reconciled" and any(item["status"] != "available_for_review" for item in
            rows(connection, prerequisites, prerequisites.c.decision_id == identifier)):
        fail(409, "prerequisites_unresolved", "Unresolved evidence requires reconciliation or deferral.")
    if request.outcome == "reconciled" and any(not set(request.evidence_refs).intersection(item["source_refs"])
            for item in rows(connection, prerequisites, prerequisites.c.decision_id == identifier)):
        fail(409, "missing_prerequisite_support", "Cite support for every required evidence category.")
    available = {item["id"] for item in decision["snapshot"]["evidence"] if item["quality"]["state"] != "unavailable"}
    if not set(request.evidence_refs) <= available or (request.outcome == "reconciled" and not request.evidence_refs):
        fail(409, "invalid_support", "Choose current available evidence from this patient snapshot.")
    follow_up = [action.strip() for action in request.follow_up]
    if any(not action or len(action) > 500 for action in follow_up):
        fail(422, "invalid_follow_up", "Follow-up actions must contain 1 to 500 characters.")
    if request.outcome == "follow_up_required" and not follow_up:
        fail(422, "follow_up_required", "Record the required follow-up actions.")
    event(connection, decision, actor, "evidence_reviewed", source_refs=request.evidence_refs,
          snapshot=decision["snapshot_hash"])
    connection.execute(records.insert().values(id=uuid4().hex, decision_id=identifier,
        patient_id=decision["patient_id"], actor=actor, outcome=request.outcome, rationale=request.rationale,
        recorded=now(), source_refs=request.evidence_refs, rule_key=decision["rule_key"],
        policy_id=decision["policy_id"], snapshot=decision["snapshot"], follow_up=follow_up))
    connection.execute(decisions.update().where(decisions.c.id == identifier).values(
        status="decided", revision=decision["revision"] + 1, updated=now()))
    event(connection, decision, actor, "decision_recorded", outcome=request.outcome,
          rationale=request.rationale, source_refs=request.evidence_refs,
          snapshot=decision["snapshot_hash"], follow_up=follow_up)
    return view(connection, get(connection, actor, identifier))


def start_follow_up(connection, actor, identifier, index):
    decision = get(connection, actor, identifier)
    record_rows = rows(connection, records, records.c.decision_id == identifier)
    if not record_rows or not 0 <= index < len(record_rows[0]["follow_up"]):
        fail(404, "follow_up_unavailable", "Follow-up action unavailable.")
    previous = rows(connection, audit, audit.c.decision_id == identifier, audit.c.action == "follow_up_initiated")
    if not any(item["detail"].get("index") == index for item in previous):
        event(connection, decision, actor, "follow_up_initiated", index=index,
              action_text=record_rows[0]["follow_up"][index])
    return view(connection, decision)


def create_policy(connection, actor, request):
    if policy_for(connection, request.id):
        fail(409, "policy_exists", "Policy IDs are immutable. Create a new version ID.")
    definition = {"due_at": request.due_at.isoformat(), "due_soon_seconds": request.due_soon_seconds,
                  "illustrative": True}
    connection.execute(policies.insert().values(id=request.id, version=request.version,
        source="Explicit synthetic illustration. No clinical timing approval.", status="active",
        definition=definition, created=now(), actor=actor))
    return policy_for(connection, request.id)


def policy_state(connection, actor, identifier, request):
    if not policy_for(connection, identifier):
        fail(404, "policy_unavailable", "Timing policy unavailable.")
    connection.execute(policies.update().where(policies.c.id == identifier).values(status=request.status))
    return policy_for(connection, identifier)


def assign_policy(connection, actor, identifier, request):
    decision = current(connection, actor, identifier, request.revision)
    if decision["status"] in TERMINAL:
        fail(409, "terminal_decision", "Create a new decision for a new review.")
    policy = policy_for(connection, request.policy_id)
    if request.policy_id and (not policy or policy["status"] != "active"):
        fail(409, "inactive_policy", "An active registered policy is required.")
    connection.execute(decisions.update().where(decisions.c.id == identifier).values(policy_id=request.policy_id))
    event(connection, decision, actor, "timing_policy_assigned", policy_id=request.policy_id)
    return view(connection, evaluate(connection, get(connection, actor, identifier)))


def initial_fixture(connection):
    active = rows(connection, decisions, decisions.c.patient_id == "demo-amira", decisions.c.archived.is_(False))
    return all(item["purpose"] == "amira-fixture" and item["status"] in {"awaiting_evidence", "ready_for_review"}
               and not item["last_investigation_id"] and item["policy_id"] is None for item in active)


def archive_for_reset(connection, actor):
    for item in rows(connection, decisions, decisions.c.patient_id == "demo-amira", decisions.c.archived.is_(False)):
        connection.execute(decisions.update().where(decisions.c.id == item["id"]).values(archived=True))
        event(connection, item, actor, "decision_archived", reason="Canonical Amira demo reset")


def investigation_runs(connection, actor, identifier):
    from app.investigation.schema_v1 import runs
    from app.investigation.service import get as get_run
    decision = get(connection, actor, identifier, active=False)
    identifiers = connection.execute(select(runs.c.id).where(
        runs.c.patient_id == decision["patient_id"],
        runs.c.detail["decision_context"]["decision_id"].as_string() == identifier
    ).order_by(runs.c.created.desc()).limit(20)).scalars()
    return [get_run(connection, actor, run_id) for run_id in identifiers]


def prepare_investigation(connection, actor, identifier, request):
    decision = evaluate(connection, get(connection, actor, identifier))
    if decision["status"] in TERMINAL:
        fail(409, "terminal_decision", "A finished decision cannot start an investigation.")
    required = rows(connection, prerequisites, prerequisites.c.decision_id == identifier)
    question = ("Investigate evidence readiness for prevention decision " + identifier + ", obligation "
                + decision["obligation_id"] + ". Prerequisites: "
                + "; ".join(item["category"] + "=" + item["status"] for item in required)
                + ". Inspect required source evidence using authorized tools. Cite tool item.id, never the context IDs. "
                  "List any prerequisite/source conflicts and abstain when conflicts remain. "
                  "Report source facts only. Timing and clinical decisions stay with the backend and human reviewer.")
    binding = {"decision_id": identifier, "patient_id": decision["patient_id"],
               "snapshot_hash": decision["snapshot_hash"], "revision": decision["revision"]}
    return {"question": question, "binding": binding, "request_id": request.request_id}


def validate_binding(connection, binding):
    decision = get(connection, "coordinator", binding["decision_id"])
    return (decision["patient_id"] == binding["patient_id"] and decision["snapshot_hash"] == binding["snapshot_hash"]
            and decision["revision"] == binding["revision"] and decision["status"] not in TERMINAL)


def finish_investigation(connection, actor, identifier, run):
    from app.investigation import service as investigation
    decision = get(connection, actor, identifier, active=False)
    if run["status"] == "running":
        return run
    previous = rows(connection, audit, audit.c.decision_id == identifier)
    if any(item["detail"].get("run_id") == run["id"] for item in previous):
        return run
    connection.execute(decisions.update().where(decisions.c.id == identifier).values(last_investigation_id=run["id"]))
    action = "evidence_retrieved" if run["detail"]["evidence_references"] else "investigation_abstained"
    event(connection, decision, actor, action, run_id=run["id"],
          tool_calls=len(run["detail"]["tool_history"]), evidence_refs=run["detail"]["evidence_references"])
    binding = run["detail"].get("decision_context")
    if binding and not decision["archived"] and validate_binding(connection, binding) and run["detail"].get("packet"):
        run = investigation.submit(connection, actor, run["id"])
    return run
