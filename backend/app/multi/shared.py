"""Bounded source projections and request-local retrieval reuse; originals remain authoritative."""
import json
from app.clinical.normalize import digest
from app.investigation import tooling
from app.investigation.provider import ProviderFailure

PERMISSIONS = {
    "A01": tuple(tooling.TOOLS),
    # Specialists intentionally have no callable tools: narrower than the recommended allowlists.
    # They read only backend-scoped, retrieved and validated evidence projections.
    "A02": (), "A03": (), "A04": (),
}
LIMITS = {"global_model_calls": 7, "a01_model_calls": 4, "specialist_model_calls": 1,
          "tool_calls": 5, "context_characters": 48000, "shared_characters": 24000,
          "evidence_items": 16, "excerpt_characters": 600, "workflow_seconds": 180}

def projection(item):
    keys = ("id", "patient_id", "kind", "version", "digest", "source", "resource_id",
            "clinical_time", "event_time", "received", "supersedes", "quality", "citation")
    values = item["normalized"].get("values", {})
    key = next(iter(values), "")
    excerpt = (item.get("content") or "")[:100]
    support = {"evidence_id": item["id"], "version": item["version"], "excerpt": excerpt,
               "value_key": key, "value_json": json.dumps(values[key]) if key else ""} if key or excerpt else None
    return {**{k: item.get(k) for k in keys}, "normalized": item["normalized"],
            "support_template": support,
            "content": (item.get("content") or "")[:LIMITS["excerpt_characters"]]}

def select_context(evidence, decision):
    refs = {ref for p in (decision or {}).get("prerequisites", []) for ref in p["source_refs"]}
    ordered = sorted(evidence, key=lambda x: (x["id"] not in refs,
                     x["quality"]["state"] not in {"conflicting", "superseded"}, x["id"]))
    result, size = [], 0
    for item in ordered[:LIMITS["evidence_items"]]:
        small = projection(item)
        length = len(json.dumps(small))
        if size + length > LIMITS["shared_characters"]:
            break
        size += length
        result.append(small)
    return result, len(result) < len(evidence)

class RetrievalCache:
    def __init__(self):
        self.cache = {}
    def execute(self, context, call):
        try:
            name = call["name"]
            arguments = tooling.TOOLS[name][0].model_validate_json(call["arguments"]).model_dump(mode="json")
            key = digest({"patient": context.patient_id, "role": context.role, "name": name, "arguments": arguments})
        except Exception:
            return tooling.execute(context, call)
        if key in self.cache:
            from app import db
            from app.clinical.access import authorize
            with db.engine.begin() as connection:
                tooling.synthetic_scope(connection, authorize(connection, context.role, context.patient_id))
            result, records, metadata = self.cache[key]
            return result, records, {**metadata, "call_id": call["call_id"], "cached": True, "duration_ms": 0}
        result, records, metadata = tooling.execute(context, call)
        metadata = {**metadata, "cached": False}
        if metadata["status"] == "ok":
            self.cache[key] = (result, records, metadata)
        return result, records, metadata

class BoundedProvider:
    def __init__(self, provider):
        self.provider = provider
    def invoke(self, messages, tools, final=False):
        compact = []
        for message in messages:
            if message.get("type") == "function_call_output":
                output = json.loads(message["output"])
                body = output.get("result")
                if isinstance(body, dict):
                    if "items" in body:
                        body = {**body, "items": [projection(x) if "normalized" in x else x for x in body["items"]]}
                    elif "normalized" in body:
                        body = projection(body)
                    output = {**output, "result": body}
                message = {**message, "output": json.dumps(output)}
            compact.append(message)
        if len(json.dumps(compact)) > LIMITS["context_characters"]:
            raise ProviderFailure("context_budget_exhausted")
        return self.provider.invoke(compact, tools, final=final)
