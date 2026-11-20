"""Provider-independent turns backed by the official OpenAI Responses SDK."""
import os
import time
from dataclasses import dataclass, field
from typing import Protocol, Literal
from urllib.parse import urlsplit

import openai
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.investigation.contracts import Draft


DEFAULT_BASE_URL = "https://api.openai.com/v1"


class Settings(BaseModel):
    llm_mode: Literal["live", "replay"] = "live"
    base_url: str = Field(default=DEFAULT_BASE_URL, max_length=2048)
    model: str = Field(default="", max_length=100)
    timeout: float = Field(default=30, ge=1, le=60)
    output_tokens: int = Field(default=2400, ge=256, le=6000)
    max_tools: int = Field(default=8, ge=1, le=16)
    max_steps: int = Field(default=6, ge=2, le=10)
    max_seconds: int = 180
    reasoning_effort: Literal['minimal', 'low', 'medium', 'high'] | None = None

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, value):
        value = value.strip() if isinstance(value, str) else value
        if not value:
            return DEFAULT_BASE_URL
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment):
            raise ValueError("Use an HTTP(S) endpoint without embedded credentials, query or fragment.")
        parsed.port
        return value.rstrip("/")

    @property
    def schema_profile(self):
        return "google_structural" if self.model.startswith("google/") else "strict"

    def public(self):
        return {**self.model_dump(), "version": "clinical-evidence-v2",
                "schema_profile": self.schema_profile,
                "cost_estimate_usd": None, "cost_estimation": "unavailable"}


def configuration():
    try:
        settings = Settings(
            llm_mode=os.getenv("LLM_MODE", "live"),
            base_url=os.getenv("OPENAI_BASE_URL", ""),
            model=os.getenv("OPENAI_MODEL", "").strip(),
            timeout=os.getenv("OPENAI_TIMEOUT_SECONDS", "30"),
            output_tokens=os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "2400"),
            max_tools=os.getenv("OPENAI_MAX_TOOL_CALLS", "8"),
            max_steps=os.getenv("OPENAI_MAX_AGENT_STEPS", "6"),
            reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT") or None)
    except ValidationError:
        return Settings(), "invalid_configuration"
    if os.getenv("CLINICAL_EVIDENCE_AGENT_ENABLED", "false").lower() != "true":
        return settings, "disabled"
    if settings.llm_mode == "replay":
        from app.investigation.replay import available
        if not settings.model:
            return settings, "missing_model: set OPENAI_MODEL to the recorded model"
        return settings, "available" if available() else "replay_unavailable: no real recording installed or DEMO_MODE disabled"
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return settings, "missing_api_key"
    # No maintained price catalog exists in this prototype. Never pretend a dollar ceiling is enforced.
    if os.getenv("OPENAI_MAX_RUN_COST_USD", "").strip():
        return settings, "cost_limit_unavailable"
    if not settings.model:
        return settings, "missing_model: set OPENAI_MODEL to an explicitly permitted model"
    return settings, "available"


class ProviderFailure(Exception):
    def __init__(self, code, retries=0, usage=None, http_status=None, model_name=None, response_id=None):
        super().__init__(code)
        self.code = code
        self.retries = retries
        self.http_status = http_status
        self.model_name = model_name
        self.response_id = response_id
        self.input_tokens = usage.input_tokens if usage else 0
        self.output_tokens = usage.output_tokens if usage else 0


@dataclass
class Turn:
    calls: list[dict] = field(default_factory=list)
    draft: Draft | None = None
    messages: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    retries: int = 0
    usage_complete: bool = True
    model_name: str | None = None
    response_id: str | None = None


class Provider(Protocol):
    def invoke(self, messages: list[dict], tools: list[dict], final: bool = False) -> Turn: ...


def strict_schema(schema):
    """Require every object field, preserving nullable optional Pydantic unions."""
    if isinstance(schema, list):
        return [strict_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = {key: strict_schema(value) for key, value in schema.items() if key != "default"}
    if result.get("type") == "object":
        result["additionalProperties"] = False
        result["required"] = list(result.get("properties", {}))
    return result


def provider_schema(schema, profile):
    """Google receives structural constraints. Full original contracts remain enforced locally."""
    if isinstance(schema, list):
        return [provider_schema(item, profile) for item in schema]
    if not isinstance(schema, dict):
        return schema
    unsupported = {"minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum",
                   "exclusiveMinimum", "exclusiveMaximum", "pattern", "format", "multipleOf"}
    return {key: provider_schema(value, profile) for key, value in schema.items()
            if profile != "google_structural" or key not in unsupported}


class OpenAIProvider:
    def __init__(self, settings):
        self.settings = settings
        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=settings.base_url,
                                    timeout=settings.timeout, max_retries=0)

    def close(self):
        self.client.close()

    def invoke(self, messages, tools, final=False):
        return self._invoke(messages, tools, final, Draft)

    def invoke_structured(self, messages, contract):
        return self._invoke(messages, [], True, contract)

    def _invoke(self, messages, tools, final, contract):
        for attempt in range(getattr(self, 'retry_attempts', 2)):
            try:
                response = self.client.responses.create(
                    model=self.settings.model, input=messages, store=False,
                    include=["reasoning.encrypted_content"],
                    max_output_tokens=self.settings.output_tokens,
                    tools=tools,
                    tool_choice="none" if final else "auto",
                    parallel_tool_calls=False,
                    **({'reasoning': {'effort': self.settings.reasoning_effort}} if self.settings.reasoning_effort else {}),
                    text={"format": {"type": "json_schema", "name": contract.__name__,
                                     "strict": True, "schema": provider_schema(strict_schema(contract.model_json_schema()),
                                                               self.settings.schema_profile)}})
                if response.status != "completed":
                    raise ProviderFailure("incomplete_response", attempt, response.usage,
                                          model_name=response.model, response_id=response.id)
                calls = []
                output = []
                for item in response.output:
                    output.append(item.model_dump(mode="json", exclude_none=True))
                    if item.type == "function_call":
                        calls.append({"name": item.name, "arguments": item.arguments,
                                      "call_id": item.call_id})
                usage = response.usage
                draft = None
                if not calls:
                    try:
                        draft = contract.model_validate_json(response.output_text)
                    except (ValueError, ValidationError):
                        raise ProviderFailure("malformed_output", attempt, response.usage,
                                              model_name=response.model, response_id=response.id) from None
                return Turn(calls=calls, draft=draft, messages=output,
                            input_tokens=usage.input_tokens if usage else 0,
                            output_tokens=usage.output_tokens if usage else 0, retries=attempt,
                            usage_complete=bool(usage) and attempt == 0,
                            model_name=response.model, response_id=response.id)
            except (openai.RateLimitError, openai.InternalServerError) as error:
                if attempt + 1 >= getattr(self, 'retry_attempts', 2):
                    raise ProviderFailure("rate_limit_or_provider_unavailable", attempt,
                                          http_status=error.status_code) from None
                time.sleep(0.25)
            except openai.APITimeoutError:
                # An unknown remote completion may have consumed tokens. Avoid replaying it.
                raise ProviderFailure("provider_timeout", attempt) from None
            except openai.AuthenticationError as error:
                raise ProviderFailure("provider_authentication", attempt, http_status=error.status_code) from None
            except openai.APIConnectionError:
                raise ProviderFailure("provider_connection", attempt) from None
            except openai.APIError as error:
                body = str(getattr(error, "body", "")).lower()
                rejected = getattr(error, "status_code", None) in {400, 403, 404, 422} and "model" in body and any(
                    word in body for word in ("not found", "not_found", "not allowed", "not permitted", "invalid", "access", "restricted", "not available"))
                code = "configured_model_rejected: check OPENAI_MODEL against models permitted by the provider and API key" if rejected else "provider_request_failed"
                raise ProviderFailure(code, attempt,
                                      http_status=getattr(error, "status_code", None)) from None
