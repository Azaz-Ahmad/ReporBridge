import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url

from app import db
from app.fhir import structure_errors
from app.main import app
from app.rules import PRE, PREG, observation, seed_records

PATIENT = "demo-amira"
ROLES = ("coordinator", "reviewer", "viewer")


@pytest.fixture
def client(tmp_path, monkeypatch):
    database = os.getenv("TEST_POSTGRES_URL")
    admin = schema = None
    if database:
        admin = create_engine(database)
        schema = "test_" + uuid4().hex
        with admin.begin() as connection:
            connection.exec_driver_sql(f"CREATE SCHEMA {schema}")
        engine = create_engine(make_url(database), connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(f"sqlite:///{(tmp_path / 'demo.db').as_posix()}")

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    monkeypatch.setattr(db, "engine", engine)
    tokens = {role: token_urlsafe() for role in ROLES}
    for role, token in tokens.items():
        monkeypatch.setenv(f"{role.upper()}_TOKEN", token)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        with TestClient(app) as api:
            def request(path, role="coordinator", method="POST", body=None):
                headers = {"Authorization": "Bearer " + tokens[role]} if role else {}
                return api.request(method, "/api" + path, headers=headers, json=body)
            yield request
    finally:
        engine.dispose()
        if admin:
            with admin.begin() as connection:
                connection.exec_driver_sql(f"DROP SCHEMA {schema} CASCADE")
            admin.dispose()


def snapshot(client):
    response = client("/snapshot", method="GET")
    assert response.status_code == 200, response.text
    return response.json()


def seed(client):
    response = client("/demo/seed")
    assert response.status_code == 200, response.text
    return snapshot(client)["clinical_obligations"][0]["id"]


def verified(client, obligation, scenario="verified"):
    response = client(f"/obligations/{obligation}/demo-completion", body={"scenario": scenario})
    assert response.status_code == 200, response.text
    return "Observation/" + response.json()["id"]


def agent(client, obligation):
    response = client(f"/obligations/{obligation}/agent")
    assert response.status_code == 200, response.text
    return response.json()["id"]


def review(client, task, decision, refs, role="reviewer"):
    return client(f"/tasks/{task}/review", role=role, body={"decision": decision, "evidence_refs": refs})


def close(client, obligation):
    return client(f"/obligations/{obligation}/close")


def test_import_and_evaluate(client):
    records = seed_records()
    assert client("/fhir/import", body={"resources": list(reversed(records))}).status_code == 200
    response = client(f"/patients/{PATIENT}/evaluate")
    assert response.status_code == 200, response.text
    item, = response.json()
    assert item["rule_key"] == PRE and item["source_id"] == records[1]["id"]
    state = snapshot(client)
    assert state["rule_versions"][0]["definition"]["source"].startswith("docs/")
    assert any(event["action"] == "obligation_created" and event["actor"] == "coordinator" for event in state["audit_events"])


@pytest.mark.parametrize("scenario", ["missing", "conflicting", "preliminary"])
def test_trigger_abstention(client, scenario):
    patient, flag = seed_records()
    records = [patient]
    if scenario == "conflicting":
        records.extend([flag, observation(PATIENT, "demo-second-flag", "follow-up-flag", "cleared")])
    if scenario == "preliminary":
        records.append({**flag, "status": "preliminary"})
    assert client("/fhir/import", body={"resources": records}).status_code == 200
    response = client(f"/patients/{PATIENT}/evaluate")
    assert response.json() == []
    assert snapshot(client)["audit_events"][0]["action"] == "rule_abstained"


def test_transition_concurrent_retry_and_dependency(client):
    previous = seed(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = list(pool.map(lambda _: client(f"/patients/{PATIENT}/pregnancy"), range(2)))
    assert all(result.status_code == 200 for result in attempts)
    state = snapshot(client)
    assert len(state["life_stage_events"]) == 1 and len(state["clinical_obligations"]) == 2
    child = next(item for item in state["clinical_obligations"] if item["rule_key"] == PREG)
    edge, = state["obligation_dependencies"]
    assert (edge["obligation_id"], edge["depends_on"], edge["rule_key"]) == (child["id"], previous, PREG)
    assert any(event["action"] == "obligation_retained_at_transition" and event["obligation_id"] == previous
               for event in state["audit_events"])
    evidence = verified(client, child["id"])
    assert review(client, agent(client, child["id"]), "approve", [evidence]).status_code == 200
    assert "linked preconception" in close(client, child["id"]).json()["reason"]


def test_registration_evaluates_unreviewed_preconception_flag(client):
    assert client("/fhir/import", body={"resources": seed_records()}).status_code == 200
    assert client(f"/patients/{PATIENT}/pregnancy").status_code == 200
    assert {item["rule_key"] for item in snapshot(client)["clinical_obligations"]} == {PRE, PREG}


def test_authorization_approval_and_success(client):
    obligation = seed(client)
    route = f"/obligations/{obligation}"
    assert client(route + "/agent", role=None).status_code == 401
    assert client(route + "/agent", role="viewer").status_code == 403
    assert client(route + "/agent", role="reviewer").status_code == 403
    task = agent(client, obligation)
    assert agent(client, obligation) == task
    execution, = snapshot(client)["agent_executions"]
    assert execution["result"]["finding"] == "missing_closure_evidence"
    assert review(client, task, "approve", [], role="coordinator").status_code == 403
    assert close(client, obligation).status_code == 409
    evidence = verified(client, obligation)
    assert review(client, task, "approve", []).status_code == 409
    assert "approval" in close(client, obligation).json()["reason"]
    assert review(client, task, "approve", [evidence]).status_code == 200
    assert review(client, task, "reject", [evidence]).status_code == 409
    assert client(route + "/close", role="reviewer").status_code == 403
    assert close(client, obligation).json() == {"status": "closed"}
    assert close(client, obligation).json() == {"status": "closed"}
    state = snapshot(client)
    closure, = state["closure_evidence"]
    assert closure["evidence_id"] == evidence.split("/")[1]
    assert state["clinical_obligations"][0]["status"] == "closed"
    actions = [event["action"] for event in state["audit_events"]]
    assert actions.count("closure_verified") == 1 and actions.count("closure_blocked") == 2


@pytest.mark.parametrize("decision", ["reject", "request_evidence"])
def test_non_approval_keeps_obligation_open(client, decision):
    obligation = seed(client)
    evidence = verified(client, obligation)
    assert review(client, agent(client, obligation), decision, [evidence]).status_code == 200
    assert close(client, obligation).status_code == 409
    assert snapshot(client)["clinical_obligations"][0]["status"] == "open"


def test_conflict_blocks_even_with_approval(client):
    obligation = seed(client)
    refs = [verified(client, obligation), verified(client, obligation, "conflicting")]
    task = agent(client, obligation)
    assert snapshot(client)["agent_executions"][0]["result"]["finding"] == "conflicting_or_unqualified_evidence"
    assert review(client, task, "approve", refs).status_code == 200
    response = close(client, obligation)
    assert response.status_code == 409 and "conflict" in response.json()["reason"]
    assert snapshot(client)["audit_events"][0]["action"] == "closure_blocked"


def test_fhir_validation_and_export(client):
    patient, evidence = seed_records()
    malformed = {**evidence, "valueQuantity": {"value": 100}}
    assert client("/fhir/import", body={"resources": [patient, malformed]}).status_code == 422
    assert snapshot(client)["patients"] == []
    assert client("/fhir/import", body={"resources": [{**patient, "meta": {}}]}).status_code == 422
    assert client("/fhir/import", body={"resources": [evidence]}).status_code == 404
    obligation = seed(client)
    assert client("/fhir/import", body={"resources": [{**evidence, "valueString": "changed"}]}).status_code == 409
    completion = verified(client, obligation)
    assert review(client, agent(client, obligation), "approve", [completion]).status_code == 200
    assert close(client, obligation).status_code == 200
    result = client(f"/fhir/patients/{PATIENT}", "viewer", "GET")
    assert result.status_code == 200, result.text
    bundle = result.json()
    assert not structure_errors(bundle)
    resources = [entry["resource"] for entry in bundle["entry"]]
    assert {"Patient", "Observation", "Task", "Provenance"} == {resource["resourceType"] for resource in resources}
    for resource in resources:
        assert not structure_errors(resource)
    task = next(resource for resource in resources if resource["resourceType"] == "Task")
    assert task["status"] == "completed" and task["output"][0]["valueReference"]["reference"] == completion


def test_imported_supporting_resources_round_trip(client):
    from app.rules import DEMO_TAG

    patient, _ = seed_records()
    base = {"meta": {"tag": [DEMO_TAG]}, "subject": {"reference": f"Patient/{PATIENT}"}}
    resources = [
        {"resourceType": "Condition", "id": "demo-condition", "code": {"text": "Synthetic history marker"}},
        {"resourceType": "DiagnosticReport", "id": "demo-report", "status": "final",
         "code": {"coding": [{"system": DEMO_TAG["system"], "code": "demo-panel"}]}},
        {"resourceType": "Encounter", "id": "demo-encounter", "status": "finished",
         "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"}},
        {"resourceType": "ServiceRequest", "id": "demo-request", "status": "draft", "intent": "proposal"},
        {"resourceType": "CarePlan", "id": "demo-plan", "status": "draft", "intent": "plan"},
    ]
    result = client("/fhir/import", body={"resources": [patient, *({**base, **item} for item in resources)]})
    assert result.status_code == 200, result.text
    assert client(f"/patients/{PATIENT}/evaluate").json() == []
    result = client(f"/fhir/patients/{PATIENT}", "viewer", "GET")
    assert result.status_code == 200
    bundle = result.json()
    assert not structure_errors(bundle)
    assert {entry["resource"]["resourceType"] for entry in bundle["entry"]} == {
        "Patient", "Condition", "DiagnosticReport", "Encounter", "ServiceRequest", "CarePlan",
    }
