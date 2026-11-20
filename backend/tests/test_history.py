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


from app.history_guard import validate as validate_history
from app.investigation.contracts import Draft
from test_investigation import configured  # noqa:F401
from app.prevention.window_grounding import explanation


@pytest.mark.parametrize("claim",["High risk","risk level is low","Elevated clinical risk","10% risk","Clinically relevant","Eligible for treatment","risk level is 10%","high-risk pregnancy"])
def test_risk_and_relevance_claims_rejected(claim):
    draft=Draft(summary=claim,findings=[],missing_information=[],conflicting_evidence=[],uncertainty=[],recommended_review_actions=[],abstained=False,scope="evidence_review")
    assert "historical_risk_or_relevance_claim" in validate_history(draft)


@pytest.mark.parametrize("unsafe",[False,True])
def test_existing_agent_retrieves_cites_and_rejects_risk(client,monkeypatch,configured,unsafe):
    start(client,monkeypatch)
    client("/v1/tsp/clock",method="GET")
    state=client("/v1/history-handoff/patients/demo-amira/receive").json()
    invoke=configured.invoke
    def wrapped(*args,**kwargs):
        turn=invoke(*args,**kwargs)
        if turn.calls:
            arguments=json.dumps({"kind":"Observation","start":"2017-01-01T00:00:00+00:00","end":"2018-01-01T00:00:00+00:00","limit":8})
            turn.calls[0]["arguments"]=arguments;turn.messages[0]["arguments"]=arguments
        if turn.draft:
            turn.draft.summary=explanation(state["window"])
            if unsafe:turn.draft.uncertainty=["This establishes high risk."]
        return turn
    configured.invoke=wrapped
    response=client("/v1/history-handoff/patients/demo-amira/investigations",body={"request_id":"history-agent"})
    assert response.status_code==200,response.text
    run=response.json();packet=run["detail"]["packet"]
    assert packet["earlier_record_context"]["rule_traces"][0]["triggered"]
    if unsafe:
        assert packet["grounding_status"]=="validation_failed" and packet["abstained"]
        assert "historical_risk_or_relevance_claim" in run["detail"]["validation"]["errors"]
    else:
        assert packet["origin"]=="model",run["detail"]["validation"]
        assert packet["findings"][0]["statement"]==history.data()["finding"]
        assert packet["findings"][0]["supporting_sources"][0]["evidence_id"] in [x["id"] for x in state["findings"]]



def test_history_reads_require_server_rule_context_on_generic_agent(client,monkeypatch,configured):
    start(client,monkeypatch);client("/v1/history-handoff/patients/demo-amira/receive")
    invoke=configured.invoke
    def wrapped(*args,**kwargs):
        turn=invoke(*args,**kwargs)
        if turn.calls:
            arguments=json.dumps({"kind":"Observation","start":"2017-01-01T00:00:00+00:00","end":"2018-01-01T00:00:00+00:00","limit":8})
            turn.calls[0]["arguments"]=arguments;turn.messages[0]["arguments"]=arguments
        return turn
    configured.invoke=wrapped
    response=client("/v1/agents/clinical-evidence/runs",body={"patient_id":"demo-amira","question":"Review the cited earlier source records for the synthetic patient.","request_id":"unbound-history","synthetic_only":True})
    assert response.status_code==200,response.text
    assert "historical_rule_context_required" in response.json()["detail"]["validation"]["errors"]
    assert response.json()["detail"]["packet"]["abstained"]


from test_workflow import agent, review, close, snapshot
from app.rules import observation, PRE, RULES
from app import history_guard
from app.investigation import service as investigations
from datetime import date, timedelta


def test_history_review_does_not_close_then_existing_evidence_gate_closes(client,monkeypatch):
    start(client,monkeypatch)
    before=client("/v1/history-handoff/patients/demo-amira/receive").json()
    obligation=before["rule_traces"][0]["obligation_ids"][0]
    record=observation("demo-amira","demo-history-reviewed",RULES[PRE]["closure"],"verified")
    record["effectiveDateTime"]=(date.fromisoformat(history.data()["registration_date"])+timedelta(days=7)).isoformat()
    assert client("/fhir/import",body={"resources":[record]}).status_code==200
    assert review(client,agent(client,obligation),"approve",["Observation/"+record["id"]]).status_code==200
    assert next(x for x in snapshot(client)["clinical_obligations"] if x["id"]==obligation)["status"]=="open"
    assert close(client,obligation).status_code==200
    after=client("/v1/history-handoff/patients/demo-amira",method="GET").json()
    assert not after["rule_traces"][0]["triggered"]
    assert [x["digest"] for x in after["findings"]]==[x["digest"] for x in before["findings"]]
    assert after["window"]["status"]=="COMPLETED_IN_WINDOW"


def test_pending_rule_change_invalidates_review_without_altering_window(client,monkeypatch,tmp_path):
    start(client,monkeypatch);client("/v1/history-handoff/patients/demo-amira/receive")
    with db.engine.begin() as connection:
        binding=history_guard.bind(connection,"coordinator","demo-amira",None)
        assert history_guard.current(connection,"coordinator",binding)
    changed=history.policy();changed["rules"][0]["equals"]="Different documented source value"
    file=tmp_path/"policy.json";file.write_text(json.dumps(changed),encoding="utf-8")
    monkeypatch.setattr(history,"POLICY_FILE",file)
    with db.engine.begin() as connection:
        assert not history_guard.current(connection,"coordinator",binding)
        from app.prevention.window_grounding import current as window_current
        assert window_current(connection,"coordinator",binding)
        with pytest.raises(HTTPException) as failure:
            investigations.sources_current(connection,"reviewer",{"patient_id":"demo-amira","detail":{"window_context":binding}})
        assert failure.value.status_code==409



@pytest.mark.parametrize("claim",["The risk is extremely high.","This finding is unrelated to pregnancy.","The patient qualifies for early testing."])
def test_free_history_narrative_cannot_add_medical_judgements(claim):
    draft=Draft(summary="Server-rendered summary",findings=[],missing_information=[],conflicting_evidence=[],uncertainty=[claim],recommended_review_actions=[],abstained=False,scope="evidence_review")
    assert "historical_narrative_not_server_approved" in validate_history(draft)
