"""Single-call structured explanation evaluations; no paid requests."""
import json,copy
import pytest
from app import explanations as ex
from app.investigation import provider
from test_workflow import client


def setup(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true");monkeypatch.setenv("CLINICAL_EVIDENCE_AGENT_ENABLED","true")
    monkeypatch.setenv("OPENAI_API_KEY","test-key");monkeypatch.setenv("EXPLANATION_MODEL","test-fields-model")
    monkeypatch.setenv("LLM_MODE","live");monkeypatch.delenv("EXPLANATION_RECORD_DIR",raising=False)
    monkeypatch.delenv("OPENAI_MAX_RUN_COST_USD",raising=False)
    assert client("/v1/tsp/demo/reset").status_code==200
    return []


def fake(monkeypatch,calls,mutate=None):
    def invoke(settings,messages):
        calls.append((settings,messages));data=json.loads(messages[1]["content"])
        if mutate:mutate(data)
        return provider.Turn(draft=ex.ExplanationFields.model_validate(data),input_tokens=17,output_tokens=23,model_name="reported-test-model",response_id="response-test")
    monkeypatch.setattr(ex,"invoke_live",invoke)


def request(client,kind="tsp",identifier="fields"):
    prefix="/v1/tsp" if kind=="tsp" else "/v1/history-handoff"
    return client(prefix+"/patients/demo-amira/explanations",body={"request_id":identifier})


@pytest.mark.parametrize("kind",["tsp","history"])
def test_one_call_no_tools_exact_fields_and_original_grounding(client,monkeypatch,kind):
    calls=setup(client,monkeypatch);fake(monkeypatch,calls)
    if kind=="history":
        assert client("/v1/history-handoff/seed").status_code==200
        assert client("/v1/history-handoff/patients/demo-amira/receive").status_code==200
    response=request(client,kind);assert response.status_code==200,response.text
    r=response.json();d=r["detail"]
    assert len(calls)==1 and d["usage"]["model_calls"]==1
    assert d["tool_history"]==[] and "authorized_tools" not in d["trace"]
    assert d["explanation"]["accepted"] and d["packet"]["origin"]=="model",d
    assert d["explanation"]["rendered_by"]=="server" and d["explanation"]["fallback"] is None
    assert d["validation"]["status"]!="validation_failed"
    assert d["packet"]["requires_human_review"] and d["packet"]["findings"]
    assert calls[0][0].output_tokens==6000
    if kind=="history":assert 'Hospital A' in d['explanation']['text'] and '2011-07-10' in d['explanation']['text']
    assert request(client,kind).json()["id"]==r["id"] and len(calls)==1


@pytest.mark.parametrize("field",["date","status","policy","version","source_version","source_excerpt","citation","review"])
def test_any_changed_field_is_rejected_with_labelled_fallback(client,monkeypatch,field):
    calls=setup(client,monkeypatch)
    def change(d):
        if field=="date":d["windows"][0]["window_end"]="2027-01-01"
        elif field=="status":d["status"]="WINDOW_PASSED"
        elif field=="policy":d["policy_id"]="invented"
        elif field=="version":d["policy_version"]="99"
        elif field=="source_version":d["cited_records"][0]["version"]+=1
        elif field=="source_excerpt":d["cited_records"][0]["excerpt"]="High risk"
        elif field=="citation":d["citation"]="invented"
        else:d["requires_human_review"]=False
    fake(monkeypatch,calls,change);r=request(client).json();d=r['detail']
    assert len(calls)==1 and not d['explanation']['accepted']
    assert d['explanation']['fallback']['label']==ex.LABEL
    assert d['packet']['origin']=='system_abstention' and d['packet']['abstained']
    assert 'human_review_queue' in d['trace']
    assert request(client).json()['detail']['explanation']['agent_abstained']


def test_unavailable_model_is_logged_with_fallback_and_no_call(client,monkeypatch):
    calls=setup(client,monkeypatch);fake(monkeypatch,calls)
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    d=request(client).json()['detail']
    assert not calls and d['usage']['model_calls']==0
    assert d['explanation']['fallback']['label']==ex.LABEL
    assert d['provider_availability']=='missing_api_key'
    assert d['packet']['origin']=='system_abstention'


def test_replay_installs_only_accepted_fields_and_runs_guards(client,monkeypatch,tmp_path):
    calls=setup(client,monkeypatch);fake(monkeypatch,calls)
    monkeypatch.setenv('EXPLANATION_RECORD_DIR',str(tmp_path))
    live=request(client).json();assert live['detail']['explanation']['accepted']
    assert len(list(tmp_path.glob('*.json')))==1
    monkeypatch.setenv('LLM_MODE','replay');monkeypatch.setenv('EXPLANATION_REPLAY_DIR',str(tmp_path))
    replay=request(client,identifier='replay').json()
    assert replay['detail']['explanation']['accepted'] and len(calls)==1,replay
    assert replay['detail']['usage']['model_calls']==0 and replay['detail']['usage']['replay_turns']==1
    client('/v1/tsp/clock',body={'as_of':'2027-01-01'})
    stale=request(client,identifier='changed').json()
    assert not stale['detail']['explanation']['accepted'] and stale['detail']['explanation']['fallback']['label']==ex.LABEL
    assert stale['detail']['usage']['model_calls']==0,stale


def test_no_patient_grant_or_wrong_role_cannot_get_explanation(client,monkeypatch):
    calls=setup(client,monkeypatch);fake(monkeypatch,calls)
    assert client('/v1/tsp/patients/demo-amira/explanations',role='viewer',body={'request_id':'viewer'}).status_code==403
    assert client('/v1/tsp/patients/demo-other/explanations',body={'request_id':'other'}).status_code==404
    assert not calls



def test_sdk_request_is_one_structured_no_tools_call(client,monkeypatch):
    import httpx,openai
    setup(client,monkeypatch);requests=[];original=openai.OpenAI
    def handler(request):
        body=json.loads(request.content);requests.append(body);fields=json.loads(body['input'][1]['content'])
        return httpx.Response(200,json={'id':'real-sdk-test','object':'response','created_at':1,'model':'reported-test-model','status':'completed','output':[{'id':'message-test','type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':json.dumps(fields),'annotations':[]}]}],'usage':{'input_tokens':20,'output_tokens':30,'total_tokens':50}})
    monkeypatch.setattr(provider.openai,'OpenAI',lambda **kw:original(**kw,http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    r=request(client).json();assert r['detail']['explanation']['accepted'],r
    assert len(requests)==1 and requests[0]['tools']==[] and requests[0]['tool_choice']=='none'
    assert requests[0]['max_output_tokens']==6000
    assert 'summary' not in requests[0]['text']['format']['schema']['properties']


def test_model_tool_attempt_never_executes(client,monkeypatch):
    setup(client,monkeypatch)
    monkeypatch.setattr(ex,'invoke_live',lambda *a:provider.Turn(calls=[{'name':'get_patient_clinical_context','arguments':'{}','call_id':'forbidden'}],input_tokens=10,output_tokens=10))
    r=request(client).json();assert r['detail']['tool_history']==[]
    assert r['detail']['error']=='explanation_unexpected_tool_calls'
    assert r['detail']['explanation']['fallback']['label']==ex.LABEL


def test_abstention_is_logged_and_never_written_as_success(client,monkeypatch,tmp_path):
    calls=setup(client,monkeypatch)
    fake(monkeypatch,calls,lambda d:d.update(abstained=True,reason='cannot_verify'))
    monkeypatch.setenv('EXPLANATION_RECORD_DIR',str(tmp_path))
    r=request(client).json();assert r['detail']['error']=='explanation_model_abstained'
    assert r['detail']['explanation']['agent_abstained'] and r['detail']['packet']['abstained']
    assert not list(tmp_path.glob('*.json'))



def test_context_changed_during_model_call_withholds_stale_rule_fallback(client,monkeypatch):
    from app import db
    from app.prevention import tsp
    from app.prevention.tsp_schema import clocks
    from sqlalchemy import select
    from datetime import date
    calls=setup(client,monkeypatch)
    def invoke(settings,messages):
        calls.append(1)
        with db.engine.begin() as connection:
            session_id=connection.execute(select(clocks.c.session_id)).scalar_one()
            tsp.clock(connection,session_id,date(2027,1,1))
        return provider.Turn(draft=ex.ExplanationFields.model_validate_json(messages[1]['content']),input_tokens=5,output_tokens=5)
    monkeypatch.setattr(ex,'invoke_live',invoke)
    r=request(client).json();d=r['detail']
    assert len(calls)==1 and not d['explanation']['accepted']
    assert 'tsp_window_context_changed' in d['validation']['errors']
    assert d['explanation']['fallback'] is None
    assert 'reload' in d['explanation']['label']



def test_server_preparation_preserves_per_source_synthetic_tag_guard(client,monkeypatch):
    from app import db
    from app.clinical.access import authorize
    from app.clinical.gateway import ClinicalRetrieval
    from test_clinical_foundation import ingest
    from datetime import datetime,UTC
    calls=setup(client,monkeypatch);fake(monkeypatch,calls)
    window=client('/v1/tsp/patients/demo-amira/window',method='GET').json()
    identifier=window['inputs_used'][0]['source_id']
    with db.engine.begin() as connection:
        resource=ClinicalRetrieval(connection,authorize(connection,'coordinator','demo-amira')).get(evidence_id=identifier).resource
    resource['meta']['tag']=[]
    assert ingest(client,resource,'untagged-synthetic-source',version=2,source='synthetic-tsp',event_time=datetime.now(UTC).isoformat()).status_code==422
    assert not calls
    # Also defend the projection if an external provider ever supplies an untagged raw resource.
    original_get=ClinicalRetrieval.get
    def untagged(self,*args,**kwargs):
        result=original_get(self,*args,**kwargs)
        if result.resource is not None:
            altered=copy.deepcopy(result.resource);altered['meta']['tag']=[]
            result=result.model_copy(update={'resource':altered})
        return result
    monkeypatch.setattr(ClinicalRetrieval,'get',untagged)
    response=request(client)
    assert response.status_code==409,response.text
    assert 'synthetic_scope_required' in response.text and not calls


def test_shipped_accepted_capsules_preserve_exact_context_and_schema():
    import json
    from app.clinical.normalize import digest
    capsules=list(ex.DEFAULT_REPLAYS.glob("*.json"))
    accepted=[json.loads(p.read_text(encoding="utf-8")) for p in capsules if "-result-" not in p.name]
    assert len(accepted)>=3
    for record in accepted:
        assert record["accepted"] is True
        assert record["schema_hash"]==ex.schema_hash()
        assert record["context_hash"]==digest(record["context"])
        assert not ex.mismatches(record["context"],ex.ExplanationFields.model_validate(record["fields"]).model_dump())
        assert not record["validation"]["errors"]
