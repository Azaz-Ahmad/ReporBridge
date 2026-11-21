import json
from datetime import datetime, UTC
import pytest
from sqlalchemy import select
from app import db, history, historical_candidates as hc
from app.clinical.schema_v1 import grants
from app.rules import PRE
from test_workflow import client, seed, snapshot, agent, review, close, verified  # noqa: F401
from test_clinical_foundation import ingest, another

BASE="/v1/historical-candidates"
def candidates(client,patient="demo-amira",role="coordinator"):
    response=client(BASE+"/patients/"+patient,method="GET",role=role)
    assert response.status_code==200,response.text
    return response.json()
def start(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true")
    assert client("/v1/history-handoff/seed").status_code==200
    before=client("/v1/tsp/patients/demo-amira/window",method="GET").json()
    old=snapshot(client)["clinical_obligations"]
    assert client("/v1/history-handoff/patients/demo-amira/receive").status_code==200
    return before,old,candidates(client)[0]
def decide(client,row,decision="confirm",rationale="Synthetic clinician review of the cited source.",role="reviewer"):
    return client(BASE+"/"+row["id"]+"/review",role=role,body={"decision":decision,"rationale":rationale})

def test_match_creates_one_separate_candidate_with_citations_and_unchanged_window(client,monkeypatch):
    before,old,row=start(client,monkeypatch)
    assert row["status"]=="candidate" and row["status_label"]=="Candidate: needs clinician confirmation"
    assert row["title"]=="Early-pregnancy glycemic screening review - identified from earlier record"
    assert row["owner_role"]=="Reviewer" and row["obligation_id"] is None
    assert row["rule_id"]==hc.policy()["rules"][0]["id"] and row["rule_version"]=="1"
    assert len(row["source_refs"])==2 and sum(item["trigger"] for item in row["source_refs"])==1
    assert all(item["provenance"]["facility"]["origin"]=="Hospital A" and item["clinical_time"].startswith("2011-07-10") for item in row["source_refs"])
    assert row["window"]==before["windows"][0] and row["clinical_confirmation"]=="pending clinical confirmation"
    assert "CITATION_PENDING" not in json.dumps(row)
    assert snapshot(client)["clinical_obligations"]==old
    assert client("/v1/tsp/patients/demo-amira/window",method="GET").json()==before
    assert client("/v1/history-handoff/patients/demo-amira/receive").status_code==200
    assert client("/patients/demo-amira/pregnancy").status_code==200
    assert len(candidates(client))==1
    events=[e for e in snapshot(client)["audit_events"] if e["action"]=="historical_candidate_identified"]
    assert len(events)==1 and events[0]["detail"]["demo_date"]=="2026-11-22"
    for source in row["source_refs"]:
        result=client(source["source_url"].removeprefix("/api"),method="GET").json()
        assert result["evidence"]["digest"]==source["digest"]

def test_nonmatching_patient_and_no_existing_preconception_obligation(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true");seed(client);another(client)
    assert client("/patients/demo-other/pregnancy").status_code==200
    assert candidates(client,"demo-other")==[]
    config=history.data();config.update(patient_id="demo-other",record_id="demo-other-earlier-observation",document_id="demo-other-earlier-document")
    resource=history.records(config)[0]
    before=client("/v1/tsp/patients/demo-other/window",method="GET").json()
    assert ingest(client,resource,source=history.SOURCE,patient="demo-other",event_time=datetime.now(UTC).isoformat()).status_code==200
    found=candidates(client,"demo-other")
    assert len(found)==1 and found[0]["status"]=="candidate"
    assert not any(item["rule_key"]==PRE for item in snapshot(client)["clinical_obligations"] if item["patient_id"]=="demo-other")
    assert client("/v1/tsp/patients/demo-other/window",method="GET").json()==before
    assert client(BASE+"/patients/demo-other",method="GET",role="reviewer").status_code==404

def test_pregnancy_registration_detects_preexisting_record_with_session_demo_date(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true");seed(client)
    assert client("/v1/tsp/clock",body={"as_of":"2026-11-25"}).status_code==200
    record=history.records(history.data())[0]
    assert ingest(client,record,source=history.SOURCE,event_time=datetime.now(UTC).isoformat()).status_code==200
    assert candidates(client)==[]
    assert client("/patients/demo-amira/pregnancy").status_code==200
    row=candidates(client)[0]
    assert row["demo_date"]=="2026-11-25"
    event=next(e for e in snapshot(client)["audit_events"] if e["action"]=="historical_candidate_identified")
    assert event["detail"]["demo_date"]=="2026-11-25"

def test_confirm_creates_distinct_normal_obligation_without_bypassing_closure(client,monkeypatch):
    before,old,row=start(client,monkeypatch)
    response=decide(client,row);assert response.status_code==200,response.text
    approved=response.json();assert approved["status"]=="confirmed"
    normal=next(item for item in snapshot(client)["clinical_obligations"] if item["id"]==approved["obligation_id"])
    assert normal["status"]=="open" and normal["owner"]=="Reviewer" and normal["id"] not in [item["id"] for item in old]
    assert close(client,normal["id"]).status_code==409
    ref=verified(client,normal["id"])
    assert close(client,normal["id"]).status_code==409
    assert review(client,agent(client,normal["id"]),"approve",[ref]).status_code==200
    assert next(item for item in snapshot(client)["clinical_obligations"] if item["id"]==normal["id"])["status"]=="open"
    assert close(client,normal["id"]).status_code==200
    assert client("/v1/tsp/patients/demo-amira/window",method="GET").json()==before
    assert decide(client,row).status_code==409

def test_dismiss_requires_rationale_is_audited_and_does_not_create_obligation(client,monkeypatch):
    before,old,row=start(client,monkeypatch)
    assert decide(client,row,"dismiss","").status_code==422
    assert decide(client,row,"dismiss","   ").status_code==422
    response=decide(client,row,"dismiss","Duplicate documentation; no further coordination candidate accepted.")
    assert response.status_code==200 and response.json()["status"]=="dismissed"
    assert snapshot(client)["clinical_obligations"]==old
    assert len([e for e in snapshot(client)["audit_events"] if e["action"]=="historical_candidate_dismissed"])==1
    assert client("/v1/history-handoff/patients/demo-amira/receive").status_code==200
    assert len(candidates(client))==1 and candidates(client)[0]["status"]=="dismissed"

@pytest.mark.parametrize("confirmed",[False,True])
def test_trigger_invalidation_withdraws_and_confirmed_care_reopens_through_existing_m08(client,monkeypatch,confirmed):
    before,old,row=start(client,monkeypatch)
    normal=None
    if confirmed:
        response=decide(client,row);assert response.status_code==200,response.text
        normal=response.json()["obligation_id"]
        ref=verified(client,normal);assert review(client,agent(client,normal),"approve",[ref]).status_code==200
        assert close(client,normal).status_code==200
    record=history.records(history.data())[0]
    response=ingest(client,record,"historical-invalidated",version=2,action="invalidate",source=history.SOURCE,event_time=datetime.now(UTC).isoformat())
    assert response.status_code==200,response.text
    assert candidates(client)[0]["status"]=="withdrawn"
    if normal:
        assert next(item for item in snapshot(client)["clinical_obligations"] if item["id"]==normal)["status"]=="open"
        assert close(client,normal).status_code==409
        assert any(e["action"]=="closure_reopened" and e["obligation_id"]==normal for e in snapshot(client)["audit_events"])
    assert decide(client,row).status_code==409
    assert len(candidates(client))==1

@pytest.mark.parametrize("role",[None,"coordinator","viewer"])
def test_only_existing_reviewer_role_can_decide(client,monkeypatch,role):
    _,_,row=start(client,monkeypatch)
    assert decide(client,row,role=role).status_code==(401 if role is None else 403)
    assert candidates(client)[0]["status"]=="candidate"

def test_revoked_grant_hides_candidate_and_prevents_confirmation(client,monkeypatch):
    _,_,row=start(client,monkeypatch)
    with db.engine.begin() as connection:
        connection.execute(grants.delete().where(grants.c.patient_id=="demo-amira",grants.c.role=="reviewer"))
    assert client(BASE+"/patients/demo-amira",method="GET",role="reviewer").status_code==404
    assert client(BASE,method="GET",role="reviewer").json()==[]
    assert decide(client,row).status_code==404

def test_policy_data_change_controls_match_without_code_changes(client,monkeypatch,tmp_path):
    monkeypatch.setenv("DEMO_MODE","true");assert client("/v1/history-handoff/seed").status_code==200
    config=history.data();config["finding"]="A different documented finding"
    seedfile=tmp_path/"history.json";seedfile.write_text(json.dumps(config));monkeypatch.setattr(history,"SEED_FILE",seedfile)
    assert client("/v1/history-handoff/patients/demo-amira/receive").status_code==200
    assert candidates(client)==[]
    definition=hc.policy();definition["rules"][0]["equals"]=config["finding"]
    file=tmp_path/"policy.json";file.write_text(json.dumps(definition));monkeypatch.setattr(hc,"POLICY_FILE",file)
    assert client("/patients/demo-amira/pregnancy").status_code==200
    assert len(candidates(client))==1

def test_candidate_confirmation_reset_archives_attested_new_lifecycle(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true")
    assert client("/v1/tsp/demo/seed").status_code==200
    _,_,row=start(client,monkeypatch)
    response=decide(client,row);assert response.status_code==200,response.text
    obligation=response.json()["obligation_id"]
    ref=verified(client,obligation);assert review(client,agent(client,obligation),"approve",[ref]).status_code==200
    assert close(client,obligation).status_code==200
    result=client("/v1/tsp/demo/reset");assert result.status_code==200,result.text
    with db.engine.begin() as connection:
        archived=connection.execute(select(hc.candidates).where(hc.candidates.c.id==row["id"])).mappings().one()
        assert archived["archived"]
    active=candidates(client)
    assert all(item["id"]!=row["id"] for item in active)
