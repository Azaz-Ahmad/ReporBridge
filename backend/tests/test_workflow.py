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

from app import db, service
from app.fhir import structure_errors
from app.main import app
from app.rules import PRE, PREG, observation, seed_records

PATIENT = "demo-amira"
ROLES = ("coordinator", "reviewer", "viewer")


@pytest.fixture
def client(tmp_path, monkeypatch, request):
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
        command.upgrade(config, getattr(request, "param", "head"))
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
    assert {event["stage"] for event in state["life_stage_events"]} == {"preconception", "pregnancy"}
    assert len(state["life_stage_events"]) == len(state["clinical_obligations"]) == 2
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
    assert review(client, task, "approve", [evidence]).status_code == 409
    updated_task = agent(client, obligation)
    assert updated_task != task
    assert review(client, updated_task, "approve", [evidence]).status_code == 200
    assert review(client, updated_task, "reject", [evidence]).status_code == 409
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
    assert result.headers["content-type"] == "application/fhir+json"
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


def test_coordination_approval_is_not_completion_authorization(client):
    obligation = seed(client)
    prior = agent(client, obligation)
    assert review(client, prior, "approve", []).status_code == 200
    assert close(client, obligation).status_code == 409
    evidence = verified(client, obligation)
    assert close(client, obligation).status_code == 409
    task = agent(client, obligation)
    assert task != prior
    assert review(client, task, "approve", [evidence]).status_code == 200
    assert close(client, obligation).status_code == 200


@pytest.mark.parametrize("failure", ["error", "interrupt"])
def test_agent_failure_records_no_review_and_allows_retry(client, monkeypatch, failure):
    obligation = seed(client)
    with monkeypatch.context() as interrupted:
        def fail(_):
            if failure == "error":
                raise TimeoutError("injected tool failure")
            return {"__interrupt__": ["injected interruption"]}
        interrupted.setattr(service.graph, "invoke", fail)
        assert client(f"/obligations/{obligation}/agent").status_code == 503
    state = snapshot(client)
    assert state["care_coordination_tasks"] == []
    assert state["agent_executions"][0]["result"]["finding"] == "failed"
    assert state["audit_events"][0]["action"] == "agent_execution_failed"
    task = agent(client, obligation)
    assert agent(client, obligation) == task
    assert len(snapshot(client)["agent_executions"]) == 2


@pytest.mark.parametrize("invalid_status", ["entered-in-error", "cancelled", "corrected", "amended"])
def test_nonfinal_completion_cannot_close(client, invalid_status):
    obligation = seed(client)
    candidate = observation(PATIENT, "demo-invalid-completion", "follow-up-reconciled", "verified")
    assert client("/fhir/import", body={"resources": [{**candidate, "status": invalid_status}]}).status_code == 200
    assert review(client, agent(client, obligation), "approve", ["Observation/demo-invalid-completion"]).status_code == 200
    assert close(client, obligation).status_code == 409


def test_new_evidence_reopens_completed_dependency_chain(client):
    prior = seed(client)
    assert client(f"/patients/{PATIENT}/pregnancy").status_code == 200
    later = next(x["id"] for x in snapshot(client)["clinical_obligations"] if x["rule_key"] == PREG)
    for identifier in (prior, later):
        evidence = verified(client, identifier)
        assert review(client, agent(client, identifier), "approve", [evidence]).status_code == 200
        assert close(client, identifier).status_code == 200
    new = observation(PATIENT, "demo-late-completion", "follow-up-reconciled", "verified")
    assert client("/fhir/import", body={"resources": [new]}).status_code == 200
    state = snapshot(client)
    assert all(item["status"] == "open" for item in state["clinical_obligations"])
    assert len(state["closure_evidence"]) == 2
    assert sum(event["action"] == "closure_reopened" for event in state["audit_events"]) == 2
    bundle = client(f"/fhir/patients/{PATIENT}", method="GET").json()
    tasks = [item["resource"] for item in bundle["entry"] if item["resource"]["resourceType"] == "Task"]
    assert all(task["status"] == "requested" and "output" not in task for task in tasks)
    assert close(client, prior).status_code == 409
    refs = [verified(client, prior), "Observation/demo-late-completion"]
    assert review(client, agent(client, prior), "approve", refs).status_code == 200
    assert close(client, prior).status_code == 200
    assert close(client, later).status_code == 409
    assert review(client, agent(client, later), "approve", [verified(client, later)]).status_code == 200
    assert close(client, later).status_code == 200
    assert len(snapshot(client)["closure_evidence"]) == 5


def test_late_source_conflict_reopens_and_prevents_closure(client):
    obligation = seed(client)
    evidence = verified(client, obligation)
    assert review(client, agent(client, obligation), "approve", [evidence]).status_code == 200
    assert close(client, obligation).status_code == 200
    conflict = observation(PATIENT, "demo-late-trigger", "follow-up-flag", "cleared")
    assert client("/fhir/import", body={"resources": [conflict]}).status_code == 200
    assert "Source evidence conflicts" in close(client, obligation).json()["reason"]


def test_fhir_references_stay_in_patient_scope(client):
    obligation = seed(client)
    other = {**seed_records()[0], "id": "demo-other"}
    candidate = observation("demo-other", "demo-unrelated-completion", "follow-up-reconciled", "verified")
    assert client("/fhir/import", body={"resources": [other, candidate]}).status_code == 200
    assert close(client, obligation).status_code == 409
    amira = observation(PATIENT, "demo-foreign-reference", "finding", "documented")
    amira["derivedFrom"] = [{"reference": "Observation/demo-unrelated-completion"}]
    assert client("/fhir/import", body={"resources": [amira]}).status_code == 422
    amira.pop("derivedFrom")
    amira["encounter"] = {"reference": "Patient/demo-amira"}
    assert client("/fhir/import", body={"resources": [amira]}).status_code == 422
    amira["encounter"] = {"reference": "Encounter/demo-visit"}
    assert client("/fhir/import", body={"resources": [amira]}).status_code == 422
    encounter = {"resourceType": "Encounter", "id": "demo-visit", "meta": amira["meta"],
                 "subject": amira["subject"], "status": "finished",
                 "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"}}
    assert client("/fhir/import", body={"resources": [amira, encounter]}).status_code == 200
    bundle = client(f"/fhir/patients/{PATIENT}", method="GET").json()
    assert any(entry["fullUrl"].endswith("/Encounter/demo-visit") for entry in bundle["entry"])
    assert not any(entry["fullUrl"].endswith("/Patient/demo-other") for entry in bundle["entry"])


def test_duplicate_role_token_fails_closed(client, monkeypatch):
    token = token_urlsafe()
    monkeypatch.setenv("COORDINATOR_TOKEN", token)
    monkeypatch.setenv("REVIEWER_TOKEN", token)
    with TestClient(app) as api:
        for headers in ({}, {"Authorization": "Bearer invalid"}, {"Authorization": "Bearer " + token}):
            assert api.get("/api/session", headers=headers).status_code == 401


def test_configured_rule_cannot_drift_without_version(client, monkeypatch):
    existing = seed(client)
    monkeypatch.setitem(service.RULES, PRE, {**service.RULES[PRE], "closure": "changed-without-version"})
    assert client(f"/patients/{PATIENT}/evaluate").status_code == 409
    assert snapshot(client)["clinical_obligations"][0]["id"] == existing
    assert client(f"/patients/{PATIENT}/pregnancy").status_code == 409
    assert snapshot(client)["patients"][0]["stage"] == "preconception"


def test_invalid_stage_does_not_mutate_timeline(client):
    seed(client)
    with db.engine.begin() as connection:
        connection.execute(db.patients.update().values(stage="unsupported"))
    assert client(f"/patients/{PATIENT}/pregnancy").status_code == 409
    assert len(snapshot(client)["life_stage_events"]) == 1


def test_dependency_constraints_and_corruption_fail_closed(client):
    from sqlalchemy.exc import IntegrityError

    prior = seed(client)
    assert client(f"/patients/{PATIENT}/pregnancy").status_code == 200
    later = next(row["id"] for row in snapshot(client)["clinical_obligations"] if row["rule_key"] == PREG)
    kind = "requires_verified_closure"
    for target in (prior, "missing-parent"):
        with pytest.raises(IntegrityError), db.engine.begin() as connection:
            connection.execute(db.dependencies.insert().values(
                id=uuid4().hex, obligation_id=later, depends_on=target, rule_key=PREG, kind=kind))
    with db.engine.begin() as connection:
        # Simulate an out-of-band reverse edge, outside any API.
        connection.execute(db.dependencies.insert().values(
            id=uuid4().hex, obligation_id=prior, depends_on=later, rule_key=PRE, kind=kind))
    evidence = verified(client, prior)
    assert review(client, agent(client, prior), "approve", [evidence]).status_code == 200
    assert close(client, prior).status_code == 409


@pytest.mark.parametrize("client", ["0001"], indirect=True)
def test_migrate_legacy_patient_reopens_closed_obligation(client):
    from app.rules import RULES

    patient, flag = seed_records()
    timestamp = service.now()
    assert client("/health", role=None, method="GET").status_code == 503
    with db.engine.begin() as connection:
        connection.execute(db.patients.insert().values(id=PATIENT, resource=patient, stage="preconception"))
        connection.execute(db.evidence.insert().values(id=flag["id"], resource=flag, patient_id=PATIENT))
        connection.execute(db.pathways.insert().values(id="preconception", label="Preconception"))
        connection.execute(db.rules.insert().values(id=PRE, rule_id=PRE.split("@")[0], version="1.0.0",
                                                    pathway_id="preconception", definition=RULES[PRE]))
        connection.execute(db.obligations.insert().values(id="legacy", patient_id=PATIENT, rule_key=PRE,
            source_id=flag["id"], owner="Demo care coordination", status="closed", created=timestamp))
        service.audit(connection, "coordinator", "resource_imported", PATIENT, refs=[f"Patient/{PATIENT}"])
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
    assert client("/health", role=None, method="GET").status_code == 200
    state = snapshot(client)
    assert state["clinical_obligations"][0]["status"] == "open"
    assert state["life_stage_events"][0]["stage"] == "preconception"
    assert [event["action"] for event in state["audit_events"]] == ["closure_reopened", "resource_imported"]


def test_late_revocation_marker_blocks_completed_evidence(client):
    obligation = seed(client)
    evidence = verified(client, obligation)
    assert review(client, agent(client, obligation), "approve", [evidence]).status_code == 200
    assert close(client, obligation).status_code == 200
    revocation = observation(PATIENT, "demo-revocation", "follow-up-reconciled", "revoked")
    revocation.update(status="entered-in-error", derivedFrom=[{"reference": evidence}])
    assert client("/fhir/import", body={"resources": [revocation]}).status_code == 200
    assert snapshot(client)["clinical_obligations"][0]["status"] == "open"
    assert "conflict" in close(client, obligation).json()["reason"]


def test_amira_reset_archives_completed_work_without_touching_other_patients(client):
    obligation = seed(client)
    other, flag = seed_records()
    other = {**other, "id": "demo-other"}
    flag = observation("demo-other", "demo-other-flag", "follow-up-flag", "outstanding")
    assert client("/fhir/import", body={"resources": [other, flag]}).status_code == 200
    assert client("/patients/demo-other/evaluate").status_code == 200
    assert client("/demo/reset-amira", role=None).status_code == 401
    assert client("/demo/reset-amira", role="reviewer").status_code == 403
    assert client("/demo/reset-amira", role="viewer").status_code == 403
    assert client("/demo/reset-amira").json()["status"] == "ready"
    assert client(f"/patients/{PATIENT}/pregnancy").status_code == 200
    assert close(client, obligation).status_code == 409
    evidence = verified(client, obligation)
    task = agent(client, obligation)
    state = snapshot(client)
    assert state["agent_executions"][0]["result"]["trace"] == ["retrieve", "reconcile", "prepare", "route"]
    assert review(client, task, "approve", [evidence]).status_code == 200
    assert close(client, obligation).status_code == 200
    before = snapshot(client)

    result = client("/demo/reset-amira")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "reset"
    state = snapshot(client)
    amira, = [row for row in state["patients"] if row["id"] == PATIENT]
    initial, = [item for item in state["clinical_obligations"] if item["patient_id"] == PATIENT]
    assert amira["stage"] == "preconception"
    assert initial["id"] != obligation and initial["status"] == "open"
    assert state["obligation_dependencies"] == []
    assert state["closure_evidence"] == []
    for table in ("clinical_evidence", "clinical_obligations", "life_stage_events", "audit_events"):
        assert [row for row in state[table] if row["patient_id"] == "demo-other"] == [
            row for row in before[table] if row["patient_id"] == "demo-other"]
    with db.engine.connect() as connection:
        archive = service.find(connection, db.demo_archive, result.json()["archive_id"], required=True)
    assert archive["records"]["closure_evidence"] == before["closure_evidence"]
    assert archive["records"]["audit_events"] == sorted(
        [row for row in before["audit_events"] if row["patient_id"] == PATIENT], key=lambda event: event["sequence"])
    assert state["demo_run_archive"][0]["audit_count"] == len(archive["records"]["audit_events"])
    assert "records" not in state["demo_run_archive"][0]
    assert client("/demo/reset-amira").json()["status"] == "ready"
    assert snapshot(client) == state


def test_amira_reset_refuses_unrelated_import_and_preserves_state(client):
    obligation = seed(client)
    assert close(client, obligation).status_code == 409
    # A run with only a blocked attempt still needs a fresh audit.
    assert client("/demo/reset-amira").json()["status"] == "reset"
    assert all(event["action"] != "closure_blocked" for event in snapshot(client)["audit_events"])
    assert client("/demo/reset-amira").json()["status"] == "ready"
    assert client(f"/patients/{PATIENT}/pregnancy").status_code == 200
    supplemental = observation(PATIENT, "demo-external-amira", "unrelated-note", "synthetic")
    assert client("/fhir/import", body={"resources": [supplemental]}).status_code == 200
    before = snapshot(client)
    response = client("/demo/reset-amira")
    assert response.status_code == 409
    assert snapshot(client) == before
