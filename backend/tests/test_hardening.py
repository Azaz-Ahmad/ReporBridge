import json
import httpx
import openai
import pytest
from app.investigation import provider


def test_no_implicit_model(monkeypatch):
    monkeypatch.setenv("CLINICAL_EVIDENCE_AGENT_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MAX_RUN_COST_USD", raising=False)
    settings, status = provider.configuration()
    assert settings.model == "" and status.startswith("missing_model")


def test_explicit_model_and_endpoint(monkeypatch):
    monkeypatch.setenv("CLINICAL_EVIDENCE_AGENT_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "permitted/example")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1/")
    monkeypatch.delenv("OPENAI_MAX_RUN_COST_USD", raising=False)
    settings, status = provider.configuration()
    assert status == "available" and settings.model == "permitted/example"
    assert settings.base_url == "https://example.test/v1"


def test_model_rejection_is_clear_without_raw_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    original = openai.OpenAI
    def handler(request):
        return httpx.Response(403, json={"error":{"message":"model access restricted secret-should-not-appear"}})
    monkeypatch.setattr(provider.openai,"OpenAI",lambda **kw:original(**kw,http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    adapter=provider.OpenAIProvider(provider.Settings(model="explicit-model"))
    with pytest.raises(provider.ProviderFailure) as error:
        adapter.invoke([],[])
    adapter.close()
    assert "configured_model_rejected" in error.value.code and "OPENAI_MODEL" in error.value.code
    assert "secret-should-not-appear" not in str(error.value)
    assert error.value.http_status == 403


from test_workflow import client, seed
from test_investigation import ScriptedProvider
from app.investigation import service
from app.prevention.window_grounding import explanation


def setup_demo(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true")
    monkeypatch.setenv("CLINICAL_EVIDENCE_AGENT_ENABLED","true")
    monkeypatch.setenv("OPENAI_MODEL","test-recorded-model")
    monkeypatch.setenv("OPENAI_API_KEY","test-key")
    monkeypatch.setenv("LLM_MODE","live")
    monkeypatch.delenv("OPENAI_MAX_RUN_COST_USD",raising=False)
    assert client("/v1/tsp/demo/reset").status_code==200


def test_record_replay_uses_real_tools_and_original_grounding(client,monkeypatch,tmp_path):
    setup_demo(client,monkeypatch)
    from app.investigation.replay import RecordingProvider, ReplayProvider
    fake=ScriptedProvider();invoke=fake.invoke
    state=client("/v1/tsp/patients/demo-amira/window",method="GET").json()
    def call(*args,**kwargs):
        turn=invoke(*args,**kwargs)
        if turn.draft:turn.draft.summary=explanation(state)
        return turn
    fake.invoke=call
    monkeypatch.setenv("LLM_RECORD_DIR",str(tmp_path))
    monkeypatch.setattr(service,"provider_factory",lambda settings:RecordingProvider(fake,settings))
    result=client("/v1/tsp/patients/demo-amira/investigations",body={"request_id":"record"}).json()
    assert result["detail"]["packet"]["origin"]=="model",result
    monkeypatch.setenv("LLM_MODE","replay");monkeypatch.setenv("LLM_REPLAY_DIR",str(tmp_path))
    monkeypatch.setattr(service,"provider_factory",lambda settings:ReplayProvider(settings))
    replay=client("/v1/tsp/patients/demo-amira/investigations",body={"request_id":"replay"}).json()
    assert replay["detail"]["validation"]==result["detail"]["validation"],replay
    assert replay["detail"]["packet"]["origin"]=="model"
    assert replay["detail"]["tool_history"] and replay["detail"]["usage"]["model_calls"]==0
    assert replay["detail"]["usage"]["replay_turns"]==2
    # Recording is a test double evaluation fixture, not a shipped or claimed live cassette.
    assert client("/v1/tsp/demo/reset").status_code==200
    reset=client("/v1/tsp/patients/demo-amira/investigations",body={"request_id":"replay-after-reset"}).json()
    assert reset["detail"]["packet"]["origin"]=="model",reset
    # A recorded unsafe conclusion still goes through the original guards.
    cassette=tmp_path/"tsp-demo-amira.json"
    original=cassette.read_text(encoding="utf-8");bad=json.loads(original)
    bad["frames"][-1]["turn"]["draft"]["summary"]="High risk"
    cassette.write_text(json.dumps(bad),encoding="utf-8")
    unsafe=client("/v1/tsp/patients/demo-amira/investigations",body={"request_id":"unsafe-replay"}).json()
    assert unsafe["detail"]["packet"]["grounding_status"]=="validation_failed"
    assert unsafe["detail"]["packet"]["origin"]=="system_abstention"
    cassette.write_text(original,encoding="utf-8")
    # Changing the clock must fail closed, never return a cached clinical conclusion.
    assert client("/v1/tsp/clock",body={"as_of":"2026-12-20"}).status_code==200
    changed=client("/v1/tsp/patients/demo-amira/investigations",body={"request_id":"changed"}).json()
    assert changed["detail"]["error"]=="replay_recording_missing_or_context_changed"
    assert changed["detail"]["packet"] is None


def test_scrub_omits_secrets_and_opaque_reasoning(monkeypatch):
    from app.investigation.replay import scrub
    monkeypatch.setenv("OPENAI_API_KEY","secret-api-key-1234")
    value=scrub({"authorization":"Bearer test","encrypted_content":"opaque","text":"secret-api-key-1234 sk-another12345"})
    assert value=={"text":"[REDACTED] [REDACTED]"}


def test_replay_missing_never_contacts_live(monkeypatch,tmp_path):
    monkeypatch.setenv("LLM_MODE","replay");monkeypatch.setenv("DEMO_MODE","true")
    monkeypatch.setenv("LLM_REPLAY_DIR",str(tmp_path));monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    monkeypatch.setenv("CLINICAL_EVIDENCE_AGENT_ENABLED","true");monkeypatch.setenv("OPENAI_MODEL","recorded-model")
    assert provider.configuration()[1].startswith("replay_unavailable")


def test_uncertain_fixture_is_attested_without_expanding_patient_grants(client,monkeypatch):
    setup_demo(client,monkeypatch)
    from app.clinical.access import authorize
    from app.investigation.tooling import synthetic_scope
    from app import db
    with db.engine.begin() as connection:
        synthetic_scope(connection,authorize(connection,"coordinator","demo-tsp-uncertain"))
    assert client("/v1/tsp/patients/demo-tsp-uncertain/window",method="GET").json()["status"]=="HOLD_DATING_UNCERTAIN"


@pytest.mark.parametrize("case",["tsp-amira","history-amira","tsp-uncertain"])
def test_recorder_fixture_setup_has_no_model_calls(case,tmp_path):
    import os,subprocess,sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    result=subprocess.run([sys.executable,str(root/"scripts/record_demo_llm.py"),"--setup-only","--execute",case,"--output",str(tmp_path)],env={**os.environ,"OPENAI_API_KEY":"synthetic-test-key-no-live-use"},capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert '"live_calls": 0' in result.stdout
    assert not list(tmp_path.glob("*.json"))



def test_replay_ignores_ingestion_time_but_retains_clinical_content():
    from app.investigation.replay import Binding
    import copy
    binding=Binding.__new__(Binding);binding.aliases={}
    source={"id":"source","resource_id":"resource","digest":"d","version":1,"clinical_time":"2011-07-10","received":"one","event_time":"one","quality":{"state":"valid"},"normalized":{"source_event_time":"one","values":{"valueString":"documented"}}}
    other=copy.deepcopy(source);other["received"]="two";other["event_time"]="two";other["normalized"]["source_event_time"]="two"
    assert binding.canonical(source)==binding.canonical(other)
    for key,value in [("version",2),("digest","changed"),("clinical_time","2012-07-10"),("quality",{"state":"unavailable"})]:
        changed=copy.deepcopy(other);changed[key]=value
        assert binding.canonical(source)!=binding.canonical(changed)
    other["normalized"]["values"]["valueString"]="different"
    assert binding.canonical(source)!=binding.canonical(other)
