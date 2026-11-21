import pytest
from sqlalchemy import select
from app import db
from app.clinical.schema_v1 import grants
from test_workflow import client, seed, snapshot, verified, review, agent, close  # noqa: F401


def closed_fixture(client):
    obligation = seed(client)
    ref = verified(client, obligation)
    assert review(client, agent(client, obligation), "approve", [ref]).status_code == 200
    assert close(client, obligation).status_code == 200
    return obligation, ref.split("/", 1)[1]


def correct(client, obligation, evidence, role="coordinator"):
    return client("/v1/tsp/demo/obligations/"+obligation+"/correct-closing-evidence",role=role,
        body={"evidence_id":evidence,"confirmation":"invalidate closing synthetic evidence"})


def test_demo_correction_reopens_preserves_owner_audit_and_m08_versions(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    obligation, evidence = closed_fixture(client)
    before = snapshot(client)
    owner = next(item["owner"] for item in before["clinical_obligations"] if item["id"] == obligation)
    response = correct(client, obligation, evidence)
    assert response.status_code == 200, response.text
    assert response.json()["obligation_status"] == "open" and response.json()["owner"] == owner
    after = snapshot(client)
    assert next(item for item in after["clinical_obligations"] if item["id"] == obligation)["owner"] == owner
    actions = [item["action"] for item in after["audit_events"] if item["obligation_id"] == obligation]
    assert "closure_reopened" in actions
    assert any(item["action"] == "clinical_evidence_reassessment" for item in after["audit_events"])
    from app.clinical.gateway import LocalFHIRProvider
    from app.clinical.access import authorize
    with db.engine.begin() as connection:
        chain = [item for item in LocalFHIRProvider(connection).catalog(authorize(connection,"coordinator","demo-amira")) if item["resource_id"] == evidence]
    assert sorted((item["version"],item["status"]) for item in chain) == [(1,"final"),(2,"invalidated")]
    assert close(client, obligation).status_code == 409
    assert correct(client, obligation, evidence).status_code == 409


@pytest.mark.parametrize("role", [None,"viewer","reviewer"])
def test_demo_correction_role_gated(client, monkeypatch, role):
    monkeypatch.setenv("DEMO_MODE", "true")
    obligation, evidence = closed_fixture(client)
    assert correct(client,obligation,evidence,role).status_code == (401 if role is None else 403)
    assert snapshot(client)["clinical_obligations"][0]["status"] == "closed"


def test_demo_correction_requires_demo_grant_confirmation_and_real_closing_reference(client, monkeypatch):
    obligation, evidence = closed_fixture(client)
    monkeypatch.delenv("DEMO_MODE",raising=False)
    assert correct(client,obligation,evidence).status_code == 403
    monkeypatch.setenv("DEMO_MODE","true")
    path="/v1/tsp/demo/obligations/"+obligation+"/correct-closing-evidence"
    assert client(path,body={"evidence_id":evidence}).status_code == 422
    assert correct(client,obligation,"demo-other").status_code == 409
    with db.engine.begin() as connection:
        connection.execute(grants.delete().where(grants.c.patient_id=="demo-amira",grants.c.role=="coordinator"))
    assert correct(client,obligation,evidence).status_code == 404
    with db.engine.begin() as connection:
        assert connection.execute(select(db.obligations.c.status).where(db.obligations.c.id==obligation)).scalar_one()=="closed"
