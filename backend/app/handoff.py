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
    return {"type": "Organization", "identifier": {"system": ORGANIZATION_SYSTEM,
        "value": "hospital-a" if name == "Hospital A" else "hospital-b"}, "display": name}


def facilities():
    return [{"name": name, "simulation": True, "organization": organization(name)} for name in ("Hospital A", "Hospital B")]


def encounter(name, identifier):
    return {"resourceType": "Encounter", "id": identifier, "meta": {"tag": [DEMO_TAG]},
        "subject": {"reference": "Patient/" + PATIENT}, "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "period": {"start": TIME}, "serviceProvider": organization(name)}


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


def assign(connection, actor, obligation, team, action):
    previous = obligation["owner"]
    if previous == team:
        return
    connection.execute(db.obligations.update().where(db.obligations.c.id == obligation["id"]).values(owner=team))
    clinical.audit(connection, actor, action, PATIENT, obligation, ["Observation/" + SOURCE_ID],
        simulation=True, previous_owner=previous, owner=team,
        origin_facility=organization("Hospital A"), receiving_facility=organization("Hospital B"))


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
    return {"simulation": True, "label": "SIMULATED exchange — no external connection",
        "patient_id": patient_id, "facilities": facilities(), "origin": "Hospital A", "receiving": "Hospital B",
        "stage": patient["stage"], "obligation_id": obligation["id"], "obligation_status": obligation["status"],
        "responsible_team": obligation["owner"], "original_owner": TEAM_A,
        "owner_history": owners, "received": False, "received_at": None}
