"""Provider-independent turns backed by the official OpenAI Responses SDK."""
import os
import time
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlsplit

import openai
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.investigation.contracts import Draft


DEFAULT_BASE_URL = "https://api.openai.com/v1"


class Settings(BaseModel):
    base_url: str = Field(default=DEFAULT_BASE_URL, max_length=2048)
    model: str = Field(default="gpt-4.1-mini", min_length=1, max_length=100)
    timeout: float = Field(default=30, ge=1, le=60)
    output_tokens: int = Field(default=2400, ge=256, le=6000)
    max_tools: int = Field(default=8, ge=1, le=16)
    max_steps: int = Field(default=6, ge=2, le=10)
    max_seconds: int = 180

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

    def public(self):
        return {**self.model_dump(), "version": "clinical-evidence-v1",
                "cost_estimate_usd": None, "cost_estimation": "unavailable"}


def configuration():
    try:
        settings = Settings(
            base_url=os.getenv("OPENAI_BASE_URL", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            timeout=os.getenv("OPENAI_TIMEOUT_SECONDS", "30"),
            output_tokens=os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "2400"),
            max_tools=os.getenv("OPENAI_MAX_TOOL_CALLS", "8"),
            max_steps=os.getenv("OPENAI_MAX_AGENT_STEPS", "6"))
    except ValidationError:
        return Settings(), "invalid_configuration"
    if os.getenv("CLINICAL_EVIDENCE_AGENT_ENABLED", "false").lower() != "true":
        return settings, "disabled"
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return settings, "missing_api_key"
    # No maintained price catalog exists in this prototype. Never pretend a dollar ceiling is enforced.
    if os.getenv("OPENAI_MAX_RUN_COST_USD", "").strip():
        return settings, "cost_limit_unavailable"
    return settings, "available"


class ProviderFailure(Exception):
    def __init__(self, code, retries=0, usage=None):
        super().__init__(code)
        self.code = code
        self.retries = retries
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


class OpenAIProvider:
    def __init__(self, settings):
        self.settings = settings
        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=settings.base_url,
                                    timeout=settings.timeout, max_retries=0)

    def close(self):
        self.client.close()

    def invoke(self, messages, tools, final=False):
        for attempt in range(2):
            try:
                response = self.client.responses.create(
                    model=self.settings.model, input=messages, store=False,
                    include=["reasoning.encrypted_content"],
                    max_output_tokens=self.settings.output_tokens,
                    tools=tools, tool_choice="none" if final else "auto",
                    parallel_tool_calls=False,
                    text={"format": {"type": "json_schema", "name": "ClinicalEvidenceDraft",
                                     "strict": True, "schema": strict_schema(Draft.model_json_schema())}})
                if response.status != "completed":
                    raise ProviderFailure("incomplete_response", attempt, response.usage)
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
                        draft = Draft.model_validate_json(response.output_text)
                    except (ValueError, ValidationError):
                        raise ProviderFailure("malformed_output", attempt, response.usage) from None
                return Turn(calls=calls, draft=draft, messages=output,
                            input_tokens=usage.input_tokens if usage else 0,
                            output_tokens=usage.output_tokens if usage else 0, retries=attempt,
                            usage_complete=bool(usage) and attempt == 0)
            except (openai.RateLimitError, openai.InternalServerError):
                if attempt:
                    raise ProviderFailure("rate_limit_or_provider_unavailable", attempt) from None
                time.sleep(0.25)
            except openai.APITimeoutError:
                # An unknown remote completion may have consumed tokens. Avoid replaying it.
                raise ProviderFailure("provider_timeout", attempt) from None
            except openai.AuthenticationError:
                raise ProviderFailure("provider_authentication", attempt) from None
            except openai.APIConnectionError:
                raise ProviderFailure("provider_connection", attempt) from None
            except openai.APIError:
                raise ProviderFailure("provider_request_failed", attempt) from None
