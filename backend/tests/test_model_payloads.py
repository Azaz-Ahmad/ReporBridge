import json,re
import httpx,openai,pytest
from sqlalchemy import select
from app import db,model_payloads as payloads
from app.model_payload_schema import calls
from app.clinical.schema_v1 import grants,access_log
from app.investigation import provider
from app.investigation.contracts import Draft
from test_workflow import client,seed

def test_actual_http_bodies_usage_manifest_and_audited_role_scope(client,monkeypatch):
    seed(client);monkeypatch.setenv("OPENAI_API_KEY","synthetic-private-provider-key")
    seen=[];draft=Draft(summary="Synthetic source quote",findings=[],missing_information=[],conflicting_evidence=[],uncertainty=[],recommended_review_actions=[],abstained=True,scope="evidence_review")
    def handler(request):
        seen.append(json.loads(request.content));assert request.headers.get("authorization")
        return httpx.Response(200,json={"id":"resp-wire","object":"response","created_at":1,"status":"completed","model":"provider-reported-version",
            "output":[{"type":"message","id":"msg","role":"assistant","status":"completed","content":[{"type":"output_text","text":draft.model_dump_json(),"annotations":[]}]}],
            "usage":{"input_tokens":11,"output_tokens":17,"total_tokens":28}})
    original=openai.OpenAI
    monkeypatch.setattr(provider.openai,"OpenAI",lambda **kwargs:original(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    settings=provider.Settings(model="requested-model")
    settings._payload_scope={"run_id":"synthetic-run","actor":"coordinator","patient_id":"demo-amira"}
    adapter=provider.OpenAIProvider(settings)
    turn=adapter.invoke([{"role":"user","content":json.dumps({"patient":{"resourceType":"Patient","id":"demo-amira","name":"Amira Haddad","birthDate":"1995-04-12"}})}],[],final=True)
    adapter.close();assert turn.input_tokens==11 and len(turn.payloads)==1
    with db.engine.begin() as c:row=c.execute(select(calls)).mappings().one()
    detail=row['detail'];assert detail['request_payload']==seen[0]
    assert detail['raw_response']['id']=='resp-wire' and detail['usage']['input_tokens']==11
    assert detail['requested_model']=='requested-model' and detail['reported_model']=='provider-reported-version'
    assert detail['redaction_label']=='None applied'
    assert detail['context_manifest']['date_of_birth_present'] and detail['context_manifest']['patient_name_or_identifier_text_present']
    serialized=json.dumps(detail);assert 'synthetic-private-provider-key' not in serialized and 'authorization' not in serialized.lower()
    assert client('/v1/model-payloads/'+row['id'],method='GET',role='reviewer').status_code==200
    assert client('/v1/model-payloads/'+row['id'],method='GET',role='viewer').status_code==403
    with db.engine.begin() as c:
        assert c.execute(select(access_log).where(access_log.c.action=='model_payload_viewed')).first()
        c.execute(grants.delete().where(grants.c.patient_id=='demo-amira',grants.c.role=='reviewer'))
    assert client('/v1/model-payloads/'+row['id'],method='GET',role='reviewer').status_code==404

def test_payload_bounds_existing_secret_scrub_and_honest_replay(client):
    seed(client);scope={"run_id":"synthetic-run","actor":"coordinator","patient_id":"demo-amira"}
    with db.engine.begin() as c:
        record=payloads.persist(c,scope,{"mode":"live","original_capture_available":True,"request_payload":{"headers":{"Authorization":"Bearer synthetic-hidden-token"},"input":"sk-synthetic-secret-key123"},"raw_response":{"encrypted_content":"opaque-secret","text":"x"*70000}})
    raw=json.dumps(record);assert 'synthetic-hidden-token' not in raw and 'sk-synthetic' not in raw and 'opaque-secret' not in raw
    assert record['response_truncated'] and record['redactions'] and record['redaction_label']!='None applied'
    settings=provider.Settings(model='requested-model');settings._payload_scope=scope
    payloads.replay(settings,[record])
    payloads.replay(settings,[])
    with db.engine.begin() as c:stored=list(c.execute(select(calls).order_by(calls.c.created)).mappings())
    assert len(stored)==3 and stored[1]['detail']['replayed'] and stored[1]['detail']['response_truncated']
    assert stored[1]['detail']['redactions']==record['redactions']
    assert stored[2]['detail']['original_capture_available'] is False and stored[2]['detail']['request_payload'] is None
    assert not re.search(r'sk-[A-Za-z0-9_-]{8,}|Bearer\s+\S+',json.dumps([r['detail'] for r in stored]))
