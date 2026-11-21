import copy
from sqlalchemy import select
from app import db
from app.clinical.schema_v1 import grants
from app.draft_schema import originals,versions,approvals
from test_workflow import client,snapshot
from test_explanations import setup,fake,request

def ready(client,monkeypatch):
    calls=setup(client,monkeypatch);fake(monkeypatch,calls)
    run=request(client).json();assert run['detail']['explanation']['accepted']
    assert client('/v1/agents/clinical-evidence/runs/'+run['id']+'/submit').status_code==200
    return run,'/v1/review-drafts/'+run['id']

def test_immutable_original_versions_nonblocking_dates_and_bound_approval(client,monkeypatch):
    run,path=ready(client,monkeypatch)
    before=snapshot(client);window=client('/v1/tsp/patients/demo-amira/window',method='GET').json()
    view=client(path,method='GET',role='reviewer');assert view.status_code==200,view.text
    original=view.json()['original'];assert original['text']==run['detail']['explanation']['text']
    first=client(path+'/versions',role='reviewer',body={'text':original['text']+' Clinician draft date: 2030-01-01.','expected_version':0})
    assert first.status_code==200,first.text
    assert first.json()['date_notice'] and first.json()['original']==original
    assert first.json()['versions'][0]['role']=='reviewer'
    assert client(path+'/versions',role='reviewer',body={'text':'stale write','expected_version':0}).status_code==409
    edited=client(path+'/versions',role='reviewer',body={'text':'Clinician-authored review. Follow the calculator shown separately.','expected_version':1}).json()
    assert len(edited['versions'])==2 and edited['versions'][0]['text']==first.json()['versions'][0]['text']
    first_id=edited['versions'][0]['id'];last=edited['versions'][-1]
    assert client(path+'/approve',role='reviewer',body={'version_id':first_id,'note':'Old version cannot be approved.'}).status_code==409
    # The old API cannot silently approve the model original after edits exist.
    assert client('/v1/agents/clinical-evidence/runs/'+run['id']+'/review',role='reviewer',body={'decision':'approve_summary','note':'Attempt to bypass edited version.'}).status_code==409
    approved=client(path+'/approve',role='reviewer',body={'version_id':last['id'],'note':'Reviewed this clinician-authored version; clinical closure remains separate.'})
    assert approved.status_code==200,approved.text
    assert approved.json()['approval']['version_id']==last['id']
    assert approved.json()['approval']['version_digest']==last['digest']
    assert client(path+'/versions',role='reviewer',body={'text':'after immutable approval','expected_version':2}).status_code==409
    assert client('/v1/tsp/patients/demo-amira/window',method='GET').json()==window
    after=snapshot(client)
    for key in ['clinical_obligations','clinical_approvals','closure_evidence']:assert before[key]==after[key]
    assert {x['action'] for x in after['audit_events']} >= {'model_draft_original_recorded','clinician_draft_version_recorded','clinician_draft_version_approved'}
    with db.engine.begin() as c:
        assert c.execute(select(originals.c.text)).scalar_one()==original['text']
        assert len(list(c.execute(select(versions))))==2

def test_draft_date_notice_does_not_block_approval_and_scope_is_preserved(client,monkeypatch):
    run,path=ready(client,monkeypatch)
    assert client(path,method='GET',role='viewer').status_code==403
    assert client(path+'/versions',body={'text':'Coordinator cannot author a clinician version.','expected_version':0}).status_code==403
    edited=client(path+'/versions',role='reviewer',body={'text':'A clinician wrote 2035-12-12; calculator values are separate.','expected_version':0}).json()
    assert edited['date_notice']
    version=edited['versions'][-1]
    assert client(path+'/approve',role='reviewer',body={'version_id':version['id'],'note':'Acknowledged non-blocking date notice.'}).status_code==200
    with db.engine.begin() as c:c.execute(grants.delete().where(grants.c.patient_id=='demo-amira',grants.c.role=='reviewer'))
    assert client(path,method='GET',role='reviewer').status_code==404

def test_existing_source_current_gate_blocks_edited_approval(client,monkeypatch):
    run,path=ready(client,monkeypatch)
    version=client(path+'/versions',role='reviewer',body={'text':'Clinician review with existing evidence.','expected_version':0}).json()['versions'][0]
    assert client('/v1/tsp/clock',body={'as_of':'2026-11-25'}).status_code==200
    response=client(path+'/approve',role='reviewer',body={'version_id':version['id'],'note':'Must not bypass the original stale-context gate.'})
    assert response.status_code==409,response.text
    with db.engine.begin() as c:assert not c.execute(select(approvals)).first()

def test_abstention_cannot_be_relabelled_as_original_model_draft(client,monkeypatch):
    setup(client,monkeypatch);monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    run=request(client).json();assert run['detail']['explanation']['agent_abstained']
    assert client('/v1/review-drafts/'+run['id'],method='GET',role='reviewer').status_code==409

def test_date_notice_parser_recognizes_iso_and_full_month_dates():
    from app.drafts import dates
    assert dates('1995-04-12 and 10 July 2011')=={'1995-04-12','2011-07-10'}
