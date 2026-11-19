"""SIMULATED facility handoff. Facility names are provenance labels, never access grants."""
from app import db, service as clinical
from app.clinical.access import authorize, fail
from app.prevention.tsp import demo_enabled
from app.rules import PRE, DEMO_TAG, observation, seed_records

PATIENT = "demo-handoff"
SOURCE_ID = "demo-handoff-origin-flag"
ORGANIZATION_SYSTEM = "https://reprobridge.example/simulated-organizations"
TIME = "2026-11-01T08:00:00+00:00"
TEAM_A = "Hospital A — SIMULATED originating care team"
TEAM_B = "Hospital B — SIMULATED receiving care team"


def organization(name):
    return {"type": "Organization", "display": name}


def facilities():
    return [{"name": name, "simulation": True, "organization": organization(name)} for name in ("Hospital A", "Hospital B")]


def encounter(name, identifier):
    return {"resourceType": "Encounter", "id": identifier, "meta": {"tag": [DEMO_TAG]},
        "subject": {"reference": "Patient/" + PATIENT}, "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "period": {"start": TIME}, "serviceProvider": organization(name),
        "identifier": [{"system": ORGANIZATION_SYSTEM, "value": "hospital-a" if name == "Hospital A" else "hospital-b"}]}


def fixture():
    patient = {**seed_records()[0], "id": PATIENT,
               "name": [{"given": ["Synthetic"], "family": "Handoff Demo"}]}
    origin = encounter("Hospital A", "demo-handoff-hospital-a")
    receiving = encounter("Hospital B", "demo-handoff-hospital-b")
    flag = observation(PATIENT, SOURCE_ID, "follow-up-flag", "outstanding")
    flag.update(effectiveDateTime=TIME, performer=[organization("Hospital A")],
                encounter={"reference": "Encounter/" + origin["id"]})
    return patient, origin, receiving, flag


def require_demo():
    if not demo_enabled():
        fail(403, "demo_disabled", "SIMULATED facility exchange requires DEMO_MODE.")


def assign(connection, actor, obligation, team, action, **extra):
    previous = obligation["owner"]
    if previous == team:
        return
    connection.execute(db.obligations.update().where(db.obligations.c.id == obligation["id"]).values(owner=team))
    clinical.audit(connection, actor, action, PATIENT, obligation, ["Observation/" + SOURCE_ID],
        simulation=True, previous_owner=previous, owner=team,
        origin_facility=organization("Hospital A"), receiving_facility=organization("Hospital B"), **extra)


def seed(connection, actor):
    require_demo()
    patient, *resources = fixture()
    existing = clinical.find(connection, db.patients, PATIENT)
    if existing and existing["resource"] != patient:
        fail(409, "fixture_mismatch", "The SIMULATED handoff patient identifier is already in use.")
    clinical.import_records(connection, actor, [patient, *resources])
    clinical.evaluate(connection, actor, PATIENT)
    obligation = next(item for item in clinical.rows(connection, db.obligations,
        db.obligations.c.patient_id == PATIENT) if item["rule_key"] == PRE)
    history = clinical.rows(connection, db.audit, db.audit.c.obligation_id == obligation["id"],
                            db.audit.c.action == "simulated_handoff_origin_assigned")
    if not history:
        # Fixture data only: retain the existing coordinator-only provisioning rule.
        # Grant this one synthetic reviewer explicitly; never restore a revoked grant on replay.
        from app.clinical.schema_v1 import grants
        from sqlalchemy import select
        if not connection.execute(select(grants.c.patient_id).where(grants.c.patient_id == PATIENT,
                grants.c.role == "reviewer")).scalar_one_or_none():
            connection.execute(grants.insert().values(patient_id=PATIENT, role="reviewer"))
            clinical.audit(connection, actor, "simulated_handoff_reviewer_granted", PATIENT,
                           simulation=True, granted_role="reviewer")
        assign(connection, actor, obligation, TEAM_A, "simulated_handoff_origin_assigned")
    return view(connection, actor, PATIENT)


def view(connection, actor, patient_id):
    authorize(connection, actor, patient_id)
    if patient_id != PATIENT:
        fail(404, "fixture_unavailable", "SIMULATED handoff is unavailable for this patient.")
    obligation = next((item for item in clinical.rows(connection, db.obligations,
        db.obligations.c.patient_id == patient_id) if item["rule_key"] == PRE), None)
    if not obligation:
        fail(404, "fixture_unavailable", "Load the SIMULATED handoff fixture first.")
    history = sorted(clinical.rows(connection, db.audit, db.audit.c.obligation_id == obligation["id"]),
                     key=lambda item: item["sequence"])
    owners = [{"recorded": item["recorded"], "previous_owner": item["detail"]["previous_owner"],
               "owner": item["detail"]["owner"], "simulation": True} for item in history
              if item["action"] in {"simulated_handoff_origin_assigned", "simulated_exchange_received"}]
    patient = clinical.find(connection, db.patients, patient_id, required=True)
    received = next((item for item in history if item["action"] == "simulated_exchange_received"), None)
    return {"simulation": True, "label": "SIMULATED exchange — no external connection",
        "patient_id": patient_id, "facilities": facilities(), "origin": "Hospital A", "receiving": "Hospital B",
        "stage": patient["stage"], "obligation_id": obligation["id"], "obligation_status": obligation["status"],
        "responsible_team": obligation["owner"], "original_owner": TEAM_A,
        "owner_history": owners, "received": bool(received),
        "received_at": received["detail"]["received_at"] if received else None}



def exchanged_resources():
    import base64
    visit = encounter("Hospital A", "demo-handoff-received-visit")
    document = {"resourceType": "DocumentReference", "id": "demo-handoff-received-note",
        "meta": {"tag": [DEMO_TAG]}, "status": "current", "docStatus": "final", "date": TIME,
        "subject": {"reference": "Patient/" + PATIENT}, "type": {"coding": [{"system":
            "https://reprobridge.example/fhir/CodeSystem/demo", "code": "assessment-summary"}]},
        "author": [organization("Hospital A")], "description": "SIMULATED exchange; no external connection",
        "context": {"encounter": [{"reference": "Encounter/" + visit["id"]}], "period": {"start": TIME}},
        "content": [{"attachment": {"contentType": "text/markdown", "creation": TIME,
            "data": base64.b64encode(b"# SIMULATED exchange\nHospital A synthetic records. The preconception follow-up obligation remains unresolved; Hospital B must review original evidence.").decode("ascii")}}]}
    return visit, document


def receive(connection, actor, patient_id):
    require_demo()
    state = view(connection, actor, patient_id)
    if state["received"]:
        return state
    if state["stage"] != "pregnancy" or state["obligation_status"] != "open":
        fail(409, "transition_required", "Register pregnancy with an unresolved obligation before this SIMULATED receipt.")
    from app.clinical.contracts import Event
    from app.clinical.events import process
    from app.clinical.schema_v1 import receipts
    from sqlalchemy import select
    context = authorize(connection, actor, patient_id)
    original = fixture()[-1]
    stored = clinical.find(connection, db.evidence, SOURCE_ID, required=True)
    if stored["resource"] != original:
        fail(409, "fixture_mismatch", "The SIMULATED origin record does not match its immutable fixture.")
    # The workflow source already exists at Hospital A. Receipt materializes its original
    # version without changing its clinical meaning; new documents use the synthetic feed.
    source_event = "simulated-handoff-origin-v1"
    process(connection, context, Event(source="workflow", event_id=source_event, event_time=TIME,
        resource=original, version=1, action="put"))
    for index, resource in enumerate(exchanged_resources()):
        process(connection, context, Event(source="synthetic-hospital-a-simulated",
            event_id="simulated-handoff-resource-" + str(index) + "-v1", event_time=TIME,
            resource=resource, version=1, action="put"))
    receipt = connection.execute(select(receipts).where(receipts.c.patient_id == patient_id,
        receipts.c.source == "workflow", receipts.c.event_id == source_event)).mappings().one()
    obligation = clinical.find(connection, db.obligations, state["obligation_id"], required=True)
    assign(connection, actor, obligation, TEAM_B, "simulated_exchange_received",
        received_at=receipt["received"], origin_event_id=source_event,
        source_evidence_id=receipt["evidence_id"], transport="received via simulated exchange")
    for other in clinical.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id):
        if other["id"] != obligation["id"]:
            assign(connection, actor, other, TEAM_B, "simulated_handoff_team_assigned")
    return view(connection, actor, patient_id)


def invalidate_origin(connection, actor, patient_id):
    require_demo()
    state = view(connection, actor, patient_id)
    if not state["received"]:
        fail(409, "receipt_required", "Receive the SIMULATED origin records first.")
    from app.clinical.contracts import Event
    from app.clinical.events import process
    from app.clinical.access import now
    from app.clinical.gateway import LocalFHIRProvider
    context = authorize(connection, actor, patient_id)
    chain = [item for item in LocalFHIRProvider(connection).catalog(context) if item["resource_id"] == SOURCE_ID]
    prior = max(chain, key=lambda item: item["version"])
    if prior["status"] == "invalidated":
        return view(connection, actor, patient_id)
    if prior["source"] != "workflow" or prior["version"] != 1 or prior["resource"] != fixture()[-1]:
        fail(409, "fixture_mismatch", "Only the recorded SIMULATED origin source can be invalidated.")
    process(connection, context, Event(source="workflow", event_id="simulated-handoff-origin-invalidate-v2",
        event_time=now(), resource=prior["resource"], version=2, action="invalidate"))
    obligation = clinical.find(connection, db.obligations, state["obligation_id"], required=True)
    clinical.audit(connection, actor, "simulated_origin_invalidation_received", patient_id, obligation,
        ["Observation/" + SOURCE_ID], simulation=True, origin_facility=organization("Hospital A"),
        receiving_facility=organization("Hospital B"), transport="received via simulated exchange")
    return view(connection, actor, patient_id)
