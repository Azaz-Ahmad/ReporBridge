"""Sanitized invocation accounting; no prompts, credentials or raw documents are retained."""
import time
import json
from functools import lru_cache
from app.clinical.access import now
from app.multi.shared import canonical
from app.investigation.provider import Draft, ProviderFailure, strict_schema, provider_schema

def error_class(code, http_status=None):
    if http_status == 429:
        return "rate_limit"
    if http_status and http_status >= 500:
        return "provider_unavailable"
    if "timeout" in code or "deadline" in code:
        return "timeout"
    if "budget" in code:
        return "budget_exhausted"
    if any(x in code for x in ("scope", "unauthorized", "denied", "authentication", "patient")):
        return "authorization"
    if any(x in code for x in ("changed", "stale", "integrity", "snapshot")):
        return "stale_or_invalid_evidence"
    if any(x in code for x in ("output", "grounding", "citation")):
        return "invalid_output"
    return "provider_or_tool_failure"

@lru_cache(maxsize=16)
def schema_characters(contract, profile):
    return len(canonical(provider_schema(strict_schema(contract.model_json_schema()), profile)))

def input_references(messages, identifier):
    found = {}
    def visit(value):
        if isinstance(value, dict):
            source_id = value.get("evidence_ref", value.get("id"))
            if source_id and "version" in value and "digest" in value:
                found[(source_id, value["version"])] = {"id": source_id, "version": value["version"], "digest": value["digest"]}
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for message in messages:
        try:
            if message.get("type") == "function_call_output":
                visit(json.loads(message["output"]).get("result"))
            elif identifier != "A01" and message.get("role") == "user":
                payload = json.loads(message["content"])
                visit(payload.get("evidence", []))
        except (ValueError, TypeError, AttributeError):
            continue
    return sorted(found.values(), key=lambda x: (x["id"], x["version"]))

class MeasuredProvider:
    def __init__(self, inner, settings, agent_id="A01", deadline=None, observations=None):
        self.inner = inner
        self.settings = settings
        self.agent_id = agent_id
        self.deadline = deadline
        self.observations = observations
        self.inner.retry_attempts = 1

    def close(self):
        if callable(getattr(self.inner, "close", None)):
            self.inner.close()

    def invoke(self, messages, tools, final=False):
        return self.measure(lambda: self.inner.invoke(messages, tools, final=final), messages, tools, Draft, "A01")

    def invoke_structured(self, messages, contract):
        identifier = {"ReconciliationDraft": "A02", "ContextDraft": "A03", "GapDraft": "A04"}[contract.__name__]
        return self.measure(lambda: self.inner.invoke_structured(messages, contract), messages, [], contract, identifier)

    def measure(self, invoke, messages, tools, contract, identifier):
        start = time.perf_counter()
        metadata = {"agent_id": identifier, "started_at": now(), "attempted": True,
                    "context_characters": len(canonical(messages)),
                    "schema_characters": schema_characters(contract, self.settings.schema_profile),
                    "tool_schema_characters": len(canonical(tools)),
                    "input_evidence_references": input_references(messages, identifier)}
        try:
            if self.deadline and start >= self.deadline:
                error = ProviderFailure("workflow_deadline")
                error.not_sent = True
                metadata["attempted"] = False
                raise error
            turn = invoke()
            metadata.update(input_tokens=turn.input_tokens, output_tokens=turn.output_tokens,
                            retries=turn.retries, requested_model=self.settings.model,
                            reported_model=turn.model_name, response_id=turn.response_id,
                            requested_tools=[{"name": x["name"], "call_id": x["call_id"]} for x in turn.calls])
            turn.telemetry = metadata
            return turn
        except Exception as error:
            code = error.code if isinstance(error, ProviderFailure) else "invalid_provider_output"
            metadata.update(error=code, error_class=error_class(code, getattr(error, "http_status", None)),
                            http_status=getattr(error, "http_status", None),
                            input_tokens=getattr(error, "input_tokens", 0),
                            output_tokens=getattr(error, "output_tokens", 0),
                            retries=getattr(error, "retries", 0),
                            requested_model=self.settings.model,
                            reported_model=getattr(error, "model_name", None),
                            response_id=getattr(error, "response_id", None))
            error.telemetry = metadata
            raise
        finally:
            metadata["model_latency_ms"] = round((time.perf_counter()-start)*1000)
            if self.observations is not None:
                self.observations.append(dict(metadata))

def accounting(memory, elapsed):
    models = memory["model_history"]
    tools = memory["tool_history"]
    return {
        "model_calls": memory["usage"]["model_calls"],
        "tool_calls": sum(not x.get("cached", False) and x.get("executed", True) for x in tools),
        "tool_requests": len(tools), "cache_hits": sum(bool(x.get("cached")) for x in tools),
        "input_tokens": memory["usage"]["input_tokens"], "output_tokens": memory["usage"]["output_tokens"],
        "retries": memory["usage"]["retries"], "usage_complete": memory["usage"]["usage_complete"],
        "total_latency_ms": elapsed,
        "cumulative_model_latency_ms": sum(x.get("model_latency_ms") or 0 for x in models),
        "tool_latency_ms": sum(x.get("duration_ms", 0) for x in tools),
        "context_peak_characters": max((x.get("context_characters", 0) for x in models), default=0),
        "persistence_latency_ms": memory.get("persistence_latency_ms", 0),
        "persistence_checkpoints": memory.get("persistence_checkpoints", 0),
        "cost_estimate_usd": None, "cost_estimation": "unavailable",
        "agents": {identifier: {
            "model_calls": sum(x.get("attempted", True) for x in models if x.get("agent_id") == identifier),
            "input_tokens": sum(x["input_tokens"] for x in models if x.get("agent_id") == identifier),
            "output_tokens": sum(x["output_tokens"] for x in models if x.get("agent_id") == identifier),
            "model_latency_ms": sum(x.get("model_latency_ms") or 0 for x in models if x.get("agent_id") == identifier),
            "tool_calls": sum(not x.get("cached", False) and x.get("executed", True) for x in tools) if identifier == "A01" else 0}
            for identifier in memory["agents"]}}
