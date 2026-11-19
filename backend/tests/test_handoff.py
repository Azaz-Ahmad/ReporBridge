"""SIMULATED exchange tests use local synthetic records and no models."""
import pytest
from sqlalchemy import select
from app import db, handoff
from app.clinical.schema_v1 import grants
from app.fhir import structure_errors
from test_workflow import client, snapshot  # noqa: F401

BASE = "/v1/simulated-handoff"


def seeded(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    response = client(BASE + "/demo/seed")
    assert response.status_code == 200, response.text
    return response.json()


def test_facilities_reuse_fhir_organization_references():
    patient, origin, receiving, flag = handoff.fixture()
    assert all(not structure_errors(resource) for resource in (patient,origin,receiving,flag))
    assert origin["serviceProvider"]["display"] == "Hospital A"
    assert receiving["serviceProvider"]["display"] == "Hospital B"
    assert flag["performer"][0] == origin["serviceProvider"]


def test_seed_idempotence_and_original_owner(client, monkeypatch):
    item = seeded(client, monkeypatch)
    assert item["simulation"] and item["responsible_team"] == handoff.TEAM_A
    assert len(item["facilities"]) == 2 and not item["received"]
    original = snapshot(client)
    assert client(BASE + "/demo/seed").json() == item
    assert snapshot(client) == original


def test_scope_and_demo_controls(client, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert client(BASE + "/demo/seed").status_code == 403
    seeded(client, monkeypatch)
    assert client(BASE + "/demo/seed", role="viewer").status_code == 403
    assert client(BASE + "/patients/" + handoff.PATIENT, role=None, method="GET").status_code == 401
    with db.engine.begin() as connection:
        connection.execute(grants.delete().where(grants.c.patient_id==handoff.PATIENT,grants.c.role=="viewer"))
    assert client(BASE + "/patients/" + handoff.PATIENT, role="viewer", method="GET").status_code == 404
    assert all(item["id"] != handoff.PATIENT for item in snapshot_as_viewer(client)["patients"])


def snapshot_as_viewer(client):
    return client("/snapshot",role="viewer",method="GET").json()


from app.clinical.schema_v1 import receipts, registry
from app.clinical.normalize import digest
from test_workflow import agent, close, review, verified


def received(client, monkeypatch):
    state=seeded(client,monkeypatch)
    assert client("/patients/"+handoff.PATIENT+"/pregnancy").status_code==200
    response=client(BASE+"/patients/"+handoff.PATIENT+"/receive")
    assert response.status_code==200,response.text
    return response.json()


def test_requires_registration_then_idempotent_receipt(client,monkeypatch):
    state=seeded(client,monkeypatch)
    assert client(BASE+"/patients/"+handoff.PATIENT+"/receive").status_code==409
    state=received(client,monkeypatch)
    assert state["responsible_team"]==handoff.TEAM_B and state["original_owner"]==handoff.TEAM_A
    assert state["received"] and state["received_at"]
    assert state["owner_history"][-1]["previous_owner"]==handoff.TEAM_A
    with db.engine.begin() as connection:
        before=list(connection.execute(select(receipts).where(receipts.c.patient_id==handoff.PATIENT)).mappings())
    original=snapshot(client)
    assert client(BASE+"/patients/"+handoff.PATIENT+"/receive").json()==state
    assert snapshot(client)==original
    assert client(BASE+"/demo/seed").json()==state
    with db.engine.begin() as connection:
        assert list(connection.execute(select(receipts).where(receipts.c.patient_id==handoff.PATIENT)).mappings())==before


def test_provenance_exact_resource_and_fhir_export(client,monkeypatch):
    state=received(client,monkeypatch)
    response=client("/v1/clinical/patients/"+handoff.PATIENT+"/resources/DocumentReference/demo-handoff-received-note",method="GET")
    assert response.status_code==200,response.text
    record=response.json()
    assert record["resource"]==handoff.exchanged_resources()[1]
    assert record["evidence"]["digest"]==digest(record["resource"])
    facility=record["evidence"]["provenance"]["facility"]
    assert facility["simulation"] and facility["origin"]=="Hospital A" and facility["receiving"]=="Hospital B"
    assert facility["received_at"] and facility["transport"]=="received via simulated exchange"
    export=client("/fhir/patients/"+handoff.PATIENT,method="GET")
    assert export.status_code==200,export.text
    bundle=export.json();assert not structure_errors(bundle)
    events=[entry["resource"] for entry in bundle["entry"] if entry["resource"]["resourceType"]=="Provenance"]
    assert any(event["activity"]["text"].startswith("SIMULATED") and
        any(agent["who"].get("display")=="Hospital A" for agent in event["agent"]) for event in events)


def test_missing_patient_grant_cannot_read_imported_records(client,monkeypatch):
    received(client,monkeypatch)
    with db.engine.begin() as connection:
        connection.execute(grants.delete().where(grants.c.patient_id==handoff.PATIENT,grants.c.role=="viewer"))
        identifier=connection.execute(select(registry.c.id).where(registry.c.patient_id==handoff.PATIENT,
            registry.c.resource_id=="demo-handoff-received-note")).scalar_one()
    for path in [BASE+"/patients/"+handoff.PATIENT,
        "/v1/clinical/patients/"+handoff.PATIENT+"/evidence",
        "/v1/clinical/patients/"+handoff.PATIENT+"/evidence/"+identifier,
        "/v1/clinical/patients/"+handoff.PATIENT+"/resources/DocumentReference/demo-handoff-received-note",
        "/fhir/patients/"+handoff.PATIENT]:
        assert client(path,role="viewer",method="GET").status_code==404,path
    assert all(row["patient_id"]!=handoff.PATIENT for row in snapshot_as_viewer(client)["clinical_evidence"])


def test_origin_invalidation_uses_existing_reopen_gates(client,monkeypatch):
    state=received(client,monkeypatch);obligation=state["obligation_id"]
    ref=verified(client,obligation)
    assert review(client,agent(client,obligation),"approve",[ref]).status_code==200
    assert client(BASE+"/patients/"+handoff.PATIENT,method="GET").json()["obligation_status"]=="open"
    assert close(client,obligation).status_code==200
    response=client(BASE+"/patients/"+handoff.PATIENT+"/origin/invalidate")
    assert response.status_code==200,response.text
    assert response.json()["obligation_status"]=="open"
    assert close(client,obligation).status_code==409
    with db.engine.begin() as connection:
        chain=list(connection.execute(select(registry).where(registry.c.patient_id==handoff.PATIENT,
            registry.c.resource_id==handoff.SOURCE_ID).order_by(registry.c.version)).mappings())
    assert [item["version"] for item in chain]==[1,2]
    assert chain[1]["status"]=="invalidated" and chain[1]["supersedes"]==chain[0]["id"]
    assert chain[1]["resource"]["performer"][0]==handoff.organization("Hospital A")
    assert client(BASE+"/patients/"+handoff.PATIENT+"/origin/invalidate").json()==response.json()
    assert client(BASE+"/patients/"+handoff.PATIENT+"/receive").json()["obligation_status"]=="open"



def test_seed_does_not_restore_revoked_reviewer_grant(client,monkeypatch):
    received(client,monkeypatch)
    assert client(BASE+"/patients/"+handoff.PATIENT,role="reviewer",method="GET").status_code==200
    with db.engine.begin() as connection:
        connection.execute(grants.delete().where(grants.c.patient_id==handoff.PATIENT,grants.c.role=="reviewer"))
    assert client(BASE+"/demo/seed").status_code==200
    assert client(BASE+"/patients/"+handoff.PATIENT,role="reviewer",method="GET").status_code==404
