"""Explicitly illustrative timing fixtures, independent of Amira."""
from datetime import UTC, datetime, timedelta
from app import db, service as clinical
from app.clinical.access import fail
from app.prevention import service
from app.prevention.contracts import CreateDecision, TimingPolicy
from app.prevention.schema_v1 import decisions
from app.rules import PRE, observation, seed_records


def timing_demo(connection, actor):
    patient = {**seed_records()[0], "id": "demo-prevention-timing",
               "name": [{"given": ["Illustrative"], "family": "Timing Scenario"}]}
    existing = clinical.find(connection, db.patients, patient["id"])
    if existing and existing["resource"] != patient:
        fail(409, "fixture_mismatch", "The illustrative timing identifier is already in use.")
    clinical.import_records(connection, actor, [
        patient, observation(patient["id"], "demo-prevention-timing-flag", "follow-up-flag", "outstanding")])
    clinical.evaluate(connection, actor, patient["id"])
    linked = clinical.rows(connection, db.obligations, db.obligations.c.patient_id == patient["id"],
                           db.obligations.c.rule_key == PRE)[0]
    if service.rows(connection, decisions, decisions.c.patient_id == patient["id"]):
        return {"patient_id": patient["id"], "status": "available"}
    clock = datetime.now(UTC)
    for name, due in [("due-soon", clock + timedelta(hours=1)), ("overdue", clock - timedelta(hours=1))]:
        policy = service.create_policy(connection, actor, TimingPolicy(
            id="illustrative-" + name + "-v1", version="1.0.0", due_at=due,
            due_soon_seconds=7200, illustrative=True))
        service.create(connection, actor, CreateDecision(obligation_id=linked["id"],
            owner="Illustrative timing test team",
            rationale="Synthetic timing display scenario. This deadline has no clinical authority.",
            policy_id=policy["id"]), purpose="illustrative-timing-fixture")
    return {"patient_id": patient["id"], "status": "created"}
