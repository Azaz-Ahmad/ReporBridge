import pytest
from app.prevention.coordination import next_action, policy, project
from test_workflow import client, snapshot  # noqa: F401


@pytest.mark.parametrize("status,action", [
    ("NOT_YET_DUE", "Monitor upcoming window"), ("DUE_SOON", "Schedule assessment"),
    ("IN_WINDOW", "Send to reviewer"), ("WINDOW_PASSED", "Escalate to responsible clinician"),
    ("HOLD_DATING_UNCERTAIN", "Ask clinician to confirm dating"),
    ("COMPLETED_IN_WINDOW", None), ("COMPLETED_LATE", None),
    ("NO_POLICY", "Ask policy administrator to confirm applicable policy"), ("UNKNOWN", None)])
def test_action_by_status(status, action):
    result = next_action(status)
    assert result["action"] == action
    assert result["owner_role"] == ("Coordinator" if action else None)


def test_action_is_data_driven_and_version_bound():
    definition = policy()
    definition["actions"]["IN_WINDOW"] = {"action": "Contact assigned reviewer", "owner_role": "Coordinator"}
    assert next_action("IN_WINDOW", definition)["action"] == "Contact assigned reviewer"
    assert project({"status": "IN_WINDOW", "policy_id": "other", "policy_version": "1"})["coordination"]["action"] is None


def test_coordination_queue_preserves_calculator_and_owners(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client("/v1/tsp/demo/seed").status_code == 200
    before = snapshot(client)
    raw = client("/v1/tsp/patients/demo-amira/window", method="GET").json()
    projected = client("/v1/tsp/patients/demo-amira/coordination", method="GET").json()
    coordination = projected.pop("coordination")
    assert projected == raw
    assert coordination["action"] == "Send to reviewer"
    assert snapshot(client)["clinical_obligations"] == before["clinical_obligations"]
    queue = client("/v1/tsp/coordination-queue", method="GET", role="viewer").json()
    assert [item["patient_id"] for item in queue] == ["demo-amira"]
    assert client("/v1/tsp/patients/demo-tsp-uncertain/coordination", method="GET", role="viewer").status_code == 404
    assert client("/v1/tsp/coordination-queue", method="GET", role=None).status_code == 401
