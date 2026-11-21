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


def test_guideline_trace_reads_policy_and_authorized_sources(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client("/v1/tsp/demo/seed").status_code == 200
    assert client("/v1/history-handoff/seed").status_code == 200
    assert client("/v1/history-handoff/patients/demo-amira/receive").status_code == 200
    response = client("/v1/tsp/patients/demo-amira/guideline-trace", method="GET")
    assert response.status_code == 200, response.text
    trace = response.json()
    assert trace["source_guideline"] == "pending clinical confirmation"
    assert trace["policy_id"] == "glycemic-assessment-pregnancy" and trace["policy_version"] == "1"
    assert any("gestational day 104" in text for text in trace["eligibility_criteria"])
    assert any("168 through 202" in text for text in trace["eligibility_criteria"])
    assert trace["historical_policy"]["rules"][0]["triggered"]
    historical = [item for item in trace["supporting_evidence"] if item["provenance"].get("facility", {}).get("origin") == "Hospital A"]
    assert len(historical) == 2
    assert all(item["clinical_time"].startswith("2011-07-10") for item in historical)
    assert "CITATION_PENDING" not in response.text
    for item in trace["supporting_evidence"]:
        source = client(item["source_url"].removeprefix("/api"), method="GET")
        assert source.status_code == 200, source.text
        assert source.json()["evidence"]["version"] == item["version"]
    assert client("/v1/tsp/patients/demo-tsp-uncertain/guideline-trace",method="GET",role="viewer").status_code == 404
    assert client("/v1/tsp/patients/demo-amira/guideline-trace",method="GET",role=None).status_code == 401


def test_trace_criteria_follow_stored_policy_and_retirement(client, monkeypatch):
    from sqlalchemy import select
    from app import db
    from app.prevention.schema_v1 import policies
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client("/v1/tsp/demo/seed").status_code == 200
    with db.engine.begin() as connection:
        row = connection.execute(select(policies).where(policies.c.id == "glycemic-assessment-pregnancy")).mappings().one()
        definition = dict(row["definition"])
        definition["dating_conflict_threshold_days"] = 9
        connection.execute(policies.update().where(policies.c.id == row["id"]).values(definition=definition))
    trace = client("/v1/tsp/patients/demo-amira/guideline-trace",method="GET").json()
    assert any("9 days" in item for item in trace["eligibility_criteria"])
    assert client("/v1/prevention/policies/glycemic-assessment-pregnancy/state",body={"status":"retired"}).status_code == 200
    trace = client("/v1/tsp/patients/demo-amira/guideline-trace",method="GET").json()
    assert not trace["policy_active"] and not trace["eligibility_criteria"]
