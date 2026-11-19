"""Decision-domain and clinical boundary checks using real persisted M08 sources."""
from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select

from app import db
from app.prevention import timing
from app.prevention.schema_v1 import audit, decisions, records
from app.clinical.fixtures import TIME, coding, note, resource
from test_workflow import client, seed, snapshot  # noqa: F401
from test_clinical_foundation import another, get, ingest
from test_investigation import configured  # noqa: F401

BASE = "/v1/prevention"


def state(client, role="coordinator"):
    response = get(client, BASE + "/snapshot", role)
    assert response.status_code == 200, response.text
    return response.json()


def decision(client):
    return next(item for item in state(client)["decisions"] if not item["archived"] and item["patient_id"] == "demo-amira")


def ready(client):
    assessment = resource("Observation", "prevention-assessment", status="final",
                          code=coding("metabolic-assessment"), effectiveDateTime=TIME, valueString="Synthetic assessment for clinician reconciliation")
    assert ingest(client, assessment, "prevention-assessment").status_code == 200
    assert ingest(client, note("prevention-summary", "assessment-summary", "# Assessment\nSynthetic evidence for clinician review."),
                  "prevention-summary").status_code == 200
    return decision(client)


def transition(client, item, action="begin_review", role="reviewer"):
    return client(BASE + "/decisions/" + item["id"] + "/transition", role=role,
                  body={"action": action, "revision": item["revision"], "rationale": "Reviewer inspected current source records."})


def record(client, item, role="reviewer", **changes):
    body = {"revision": item["revision"], "outcome": "follow_up_required",
            "rationale": "Clinician requests further source reconciliation.",
            "evidence_refs": list({ref for p in item["prerequisites"] for ref in p["source_refs"]}),
            "reviewed_snapshot": item["snapshot_hash"], "follow_up": ["Obtain a clinician reconciliation note."]}
    return client(BASE + "/decisions/" + item["id"] + "/record", role=role, body={**body, **changes})


def test_creation_no_deadline_and_prerequisite_registry(client):
    original = seed(client)
    item = decision(client)
    assert item["obligation_id"] == original
    assert item["status"] == "awaiting_evidence"
    assert item["timing"]["label"] == "Timing not established."
    assert item["due_date"] is None and item["timing_policy"] is None
    assert all(p["status"] == "missing" for p in item["prerequisites"])
    assert state(client)["counts"]["awaiting_evidence"] == 1
    assert get(client, BASE + "/decisions/" + item["id"]).json()["id"] == item["id"]
    assert len(state(client)["decisions"]) == 1


def test_patient_and_reviewer_scope(client):
    seed(client)
    another(client)
    from app.rules import observation
    flag = observation("demo-other", "demo-other-flag", "follow-up-flag", "outstanding")
    assert client("/fhir/import", body={"resources": [flag]}).status_code == 200
    assert client("/patients/demo-other/evaluate").status_code == 200
    linked = next(row for row in snapshot(client)["clinical_obligations"] if row["patient_id"] == "demo-other")
    response = client(BASE + "/decisions", body={"obligation_id": linked["id"], "owner": "Synthetic other team", "rationale": "Other synthetic source review."})
    assert response.status_code == 200
    identifier = response.json()["id"]
    assert get(client, BASE + "/decisions/" + identifier, "reviewer").status_code == 404
    assert get(client, BASE + "/snapshot?patient_id=demo-other", "viewer").status_code == 404
    assert all(item["patient_id"] == "demo-amira" for item in state(client, "viewer")["decisions"])
    assert transition(client, decision(client), role="viewer").status_code == 403
    assert record(client, decision(client), role="coordinator").status_code == 403


def test_evidence_availability_and_reviewer_record_do_not_close_obligation(client):
    seed(client)
    item = ready(client)
    assert item["status"] == "ready_for_review"
    assert all(p["status"] == "available_for_review" for p in item["prerequisites"])
    reviewed = transition(client, item).json()
    assert reviewed["status"] == "under_review"
    assert record(client, item).status_code == 409
    response = record(client, reviewed, outcome="reconciled", follow_up=[])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "decided"
    clinical = snapshot(client)
    assert clinical["clinical_obligations"][0]["status"] == "open"
    assert clinical["clinical_approvals"] == [] and clinical["closure_evidence"] == []
    assert client("/obligations/" + item["obligation_id"] + "/close").status_code == 409
    assert record(client, response.json()).status_code == 409
    with db.engine.connect() as connection:
        assert len(connection.execute(select(records)).all()) == 1


def test_missing_conflicting_and_foreign_support_fail_closed(client):
    seed(client)
    item = decision(client)
    reviewed = transition(client, item).json()
    assert record(client, reviewed, outcome="reconciled", follow_up=[]).status_code == 409
    assert record(client, reviewed, evidence_refs=["foreign-source"]).status_code == 409
    response = record(client, reviewed)
    assert response.status_code == 200
    item = response.json()
    action = BASE + "/decisions/" + item["id"] + "/follow-up/0"
    assert client(action).status_code == 200
    assert client(action).status_code == 200
    assert sum(row["action"] == "follow_up_initiated" for row in state(client)["history"]) == 1
    assert client(action, role="viewer").status_code == 403


def test_correction_invalidates_review_and_preserves_history(client):
    seed(client)
    item = ready(client)
    reviewed = transition(client, item).json()
    revised = resource("Observation", "prevention-assessment", status="final", code=coding("metabolic-assessment"),
                       effectiveDateTime=TIME, valueString="Corrected synthetic review documentation.")
    assert ingest(client, revised, "assessment-v2", version=2).status_code == 200
    assert record(client, reviewed).status_code == 409
    current = decision(client)
    assert current["status"] == "ready_for_review" and current["snapshot_hash"] != reviewed["snapshot_hash"]
    assert any(row["action"] == "review_started" for row in state(client)["history"])
    conflicting = {**revised, "id": "demo-prevention-conflict", "valueString": "Different source assessment."}
    assert ingest(client, conflicting, "conflicting-assessment").status_code == 200
    assert any(p["status"] == "conflicting" for p in decision(client)["prerequisites"])


@pytest.mark.parametrize("offset,window,status", [(3600,7200,"due_soon"),(36000,7200,"scheduled"),(-1,7200,"overdue"),(0,0,"due_soon")])
def test_deterministic_timing(offset, window, status):
    clock = datetime(2026, 11, 19, tzinfo=UTC)
    policy = {"id": "illustrative-policy", "status": "active",
              "definition": {"due_at": (clock + timedelta(seconds=offset)).isoformat(), "due_soon_seconds": window}}
    assert timing.evaluate(policy, clock)["state"] == status
    for retired in ["retired", "superseded"]:
        assert timing.evaluate({**policy, "status": retired}, clock)["label"] == "Timing not established."
    assert timing.evaluate(None, clock)["due_at"] is None


def test_policy_versions_retirement_and_separate_timing_fixture(client):
    seed(client)
    item = decision(client)
    policy = {"id": "illustrative-policy-v1", "version": "1.0.0",
              "due_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
              "due_soon_seconds": 7200, "illustrative": True}
    assert client(BASE + "/policies", body=policy, role="viewer").status_code == 403
    assert client(BASE + "/policies", body={**policy,"illustrative":False}).status_code == 422
    assert client(BASE + "/policies", body=policy).status_code == 200
    assert client(BASE + "/policies", body=policy).status_code == 409
    result = client(BASE + "/decisions/" + item["id"] + "/policy",
                    body={"revision":item["revision"],"policy_id":policy["id"]}).json()
    assert result["timing"]["state"] == "due_soon"
    assert result["timing_policy"]["source"].startswith("Explicit synthetic")
    assert client(BASE + "/policies/" + policy["id"] + "/state", body={"status":"retired"}).status_code == 200
    assert decision(client)["timing"]["state"] == "not_established"
    assert client(BASE + "/demo/timing").status_code == 200
    counts = state(client)["counts"]
    assert counts["due_soon"] == 1 and counts["overdue"] == 1
    assert state(client,"viewer")["counts"]["overdue"] == 0


def test_reset_preserves_decision_audit_and_unrelated_fixture(client):
    seed(client)
    item = transition(client, decision(client)).json()
    assert record(client, item).status_code == 200
    assert client(BASE + "/demo/timing").status_code == 200
    unrelated = [d for d in state(client)["decisions"] if d["patient_id"] != "demo-amira"]
    assert client("/demo/reset-amira").status_code == 200
    current = state(client)
    assert [d for d in current["decisions"] if d["patient_id"] != "demo-amira"] == unrelated
    archived = next(d for d in current["decisions"] if d["id"] == item["id"])
    assert archived["archived"] is True and archived["record"]["outcome"] == "follow_up_required"
    assert get(client, BASE + "/decisions/" + archived["id"]).status_code == 200
    fresh = decision(client)
    assert fresh["id"] != item["id"] and fresh["status"] == "awaiting_evidence"
    assert any(row["action"] == "decision_archived" for row in current["history"])


def test_concurrent_decision_record_and_escalation(client):
    seed(client)
    item = decision(client)
    escalated = transition(client, item, action="escalate", role="coordinator").json()
    assert escalated["status"] == "escalated"
    assert transition(client, escalated, action="resume", role="coordinator").status_code == 200
    reviewed = transition(client, decision(client)).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: record(client, reviewed), range(2)))
    assert sorted(result.status_code for result in results) == [200,409]


def test_trusted_agent_binding_real_tools_and_replay(client, configured):
    seed(client)
    item = ready(client)
    configured.mode = "corrected"
    path = BASE + "/decisions/" + item["id"] + "/investigations"
    response = client(path, body={"request_id":"readiness"})
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "pending_review"
    assert run["detail"]["decision_context"]["decision_id"] == item["id"]
    assert run["detail"]["packet"]["grounding_status"] == "partially_grounded"
    assert run["detail"]["tool_history"][0]["name"] == "get_patient_clinical_context"
    count = configured.turns
    assert client(path, body={"request_id":"readiness"}).json()["id"] == run["id"]
    assert configured.turns == count
    assert client(path, body={"request_id":"spoof","patient_id":"demo-other"}).status_code == 422
    assert get(client,path).json()[0]["id"] == run["id"]
    assert decision(client)["status"] == "ready_for_review"
    assert snapshot(client)["clinical_approvals"] == []


def test_agent_cannot_invent_timing_or_record_decisions(client, configured):
    seed(client)
    item = ready(client)
    original = configured.invoke
    def invocation(*args, **kwargs):
        result = original(*args, **kwargs)
        if result.draft:
            result.draft.summary = "Review within 24 hours."
        return result
    configured.invoke = invocation
    path = BASE + "/decisions/" + item["id"] + "/investigations"
    response = client(path, body={"request_id":"timing-advice"})
    assert response.status_code == 200, response.text
    packet = response.json()["detail"]["packet"]
    assert packet["grounding_status"] == "validation_failed" and packet["abstained"]
    assert "unsupported_timing_advice" in response.json()["detail"]["validation"]["errors"]
    assert decision(client)["due_date"] is None
    with db.engine.connect() as connection:
        assert not connection.execute(select(records)).all()


def test_concurrent_agent_request_finalizes_once(client, configured):
    seed(client)
    item = ready(client)
    configured.mode = 'corrected'
    path = BASE + '/decisions/' + item['id'] + '/investigations'
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client(path, body={'request_id':'concurrent-readiness'}), range(2)))
    assert all(response.status_code == 200 for response in responses)
    assert len({response.json()['id'] for response in responses}) == 1
    assert configured.turns == 2
    run = get(client, path).json()[0]
    assert run['status'] == 'pending_review'
    events = [event for event in state(client)['history'] if event['action'] == 'evidence_retrieved']
    assert len(events) == 1


def test_changed_decision_context_rejects_request_id_reuse(client, configured):
    seed(client)
    item = ready(client)
    configured.mode = 'corrected'
    path = BASE + '/decisions/' + item['id'] + '/investigations'
    assert client(path, body={'request_id':'context-replay'}).status_code == 200
    revised = resource('Observation', 'prevention-assessment', status='final', code=coding('metabolic-assessment'),
                       effectiveDateTime=TIME, valueString='A later current assessment value.')
    assert ingest(client, revised, 'context-assessment-v2', version=2).status_code == 200
    assert client(path, body={'request_id':'context-replay'}).status_code == 409


def test_registry_rejects_an_unrelated_obligation_rule(client):
    seed(client)
    assert client('/patients/demo-amira/pregnancy').status_code == 200
    linked = next(item for item in snapshot(client)['clinical_obligations'] if item['rule_key'].startswith('pregnancy-'))
    response = client(BASE + '/decisions', body={'obligation_id':linked['id'], 'owner':'Synthetic review team',
                                                'rationale':'Attempt to apply an unrelated readiness registry.'})
    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'unsupported_readiness_rule'
