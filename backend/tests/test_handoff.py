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
