from app import db
from app.record_facilities import assign
from app.clinical.access import authorize
from app.clinical.gateway import ClinicalRetrieval
from app.clinical.contracts import Filters
from test_workflow import client, seed  # noqa:F401
import pytest
from fastapi import HTTPException


def test_facility_attribute_is_scoped_immutable_and_replayable(client):
    seed(client)
    with db.engine.begin() as connection:
        retrieval=ClinicalRetrieval(connection,authorize(connection,"coordinator","demo-amira"))
        item=retrieval.list(Filters(kind="Observation")).items[0]
        original=assign(connection,"coordinator","demo-amira",item.id,"Hospital A")
        assert assign(connection,"coordinator","demo-amira",item.id,"Hospital A")==original
        result=retrieval.get(evidence_id=item.id).evidence
        assert result.provenance["facility"]["origin"]=="Hospital A"
        assert result.digest==item.digest
        with pytest.raises(HTTPException):assign(connection,"coordinator","demo-amira",item.id,"Hospital B")
        with pytest.raises(HTTPException):assign(connection,"viewer","demo-no-grant",item.id,"Hospital A")


from app import history
from test_clinical_foundation import another
import json


def start(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true")
    r=client("/v1/history-handoff/seed");assert r.status_code==200,r.text
    return r.json()


def test_receive_source_provenance_rule_and_replay(client,monkeypatch):
    initial=start(client,monkeypatch)
    assert not initial["rule_traces"][0]["triggered"]
    r=client("/v1/history-handoff/patients/demo-amira/receive");assert r.status_code==200,r.text
    result=r.json();assert result["rule_traces"][0]["triggered"]
    assert result["age_at_record"]==22 and result["age_at_registration"]==31
    assert result["window"]["status"]==initial["window"]["status"]
    assert all(item["provenance"]["facility"]["origin"]=="Hospital A" for item in result["findings"])
    assert client("/v1/history-handoff/patients/demo-amira/receive").json()==result


def test_nonmatching_patient_has_no_historical_trigger(client,monkeypatch):
    start(client,monkeypatch);another(client)
    r=client("/v1/history-handoff/patients/demo-other",method="GET")
    assert r.status_code==200 and not r.json()["rule_traces"][0]["triggered"]
    assert client("/v1/history-handoff/patients/demo-other",role="viewer",method="GET").status_code==404


def test_swapping_seed_value_changes_rule_without_code_changes(client,monkeypatch,tmp_path):
    start(client,monkeypatch)
    assert client("/v1/history-handoff/patients/demo-amira/receive").json()["rule_traces"][0]["triggered"]
    changed=history.data();changed["finding"]="A different documented finding awaiting confirmation"
    file=tmp_path/"seed.json";file.write_text(json.dumps(changed),encoding="utf-8")
    monkeypatch.setattr(history,"SEED_FILE",file)
    result=client("/v1/history-handoff/patients/demo-amira/receive").json()
    assert not result["rule_traces"][0]["triggered"]
    assert next(x for x in result["findings"] if x["kind"]=="Observation")["version"]==2
