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
