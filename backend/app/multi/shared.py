"""Version-pinned source context and compact, source-preserving model projections."""
import copy
import json
import re
import time
from dataclasses import dataclass

from fastapi import HTTPException
from app import db
from app.clinical.access import authorize, now
from app.clinical.normalize import digest
from app.investigation import tooling
from app.investigation.provider import ProviderFailure
from app.multi.legacy_shared_v1 import PERMISSIONS, LIMITS as ORIGINAL_LIMITS

LIMITS = {**ORIGINAL_LIMITS, "a01_model_calls": 3}
MISSING = {"missing", "unavailable"}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def projection(item):
    # Keep whole retrieved sections. An oversized section is omitted, never cut mid-meaning.
    content = item.get("content") or ""
    omitted = len(content) > LIMITS["excerpt_characters"]
    excerpt = "" if omitted else content
    normalized = item["normalized"]
    values = normalized.get("values", {})
    key = next(iter(values), "")
    support = ({"evidence_id": item["id"], "version": item["version"],
                "excerpt": excerpt if not key else "", "value_key": key,
                "value_json": json.dumps(values[key]) if key else ""}
               if key or excerpt else None)
    result = {k: item.get(k) for k in (
        "id", "patient_id", "kind", "version", "digest", "source", "resource_id",
        "clinical_time", "event_time", "received", "supersedes", "quality")}
    result.update(normalized={"values": values, "codings": normalized.get("codings", []),
                              "document": {k: normalized.get("document", {}).get(k)
                                           for k in ("type", "available")
                                           if k in normalized.get("document", {})}},
                  provenance=item.get("provenance", {}), content=excerpt,
                  section=item.get("section"), excerpt_omitted=omitted,
                  support_template=support)
    return result

def select_context(evidence, decision):
    refs = {ref for p in (decision or {}).get("prerequisites", []) for ref in p["source_refs"]}
    unique = {x["id"]: x for x in evidence}
    ordered = sorted(unique.values(), key=lambda x: (
        x["id"] not in refs, x["quality"]["state"] not in {"conflicting", "superseded"}, x["id"]))
    selected, size = [], 0
    for item in ordered[:LIMITS["evidence_items"]]:
        compact = projection(item)
        length = len(canonical(compact))
        if size + length > LIMITS["shared_characters"]:
            break
        size += length
        selected.append(compact)
    return selected, len(selected) < len(unique)

@dataclass(frozen=True)
class SealedContext:
    payload_json: str
    context_id: str

    @classmethod
    def create(cls, run, scope, fingerprint, evidence, decision, trusted):
        sources, truncated = select_context(evidence, decision)
        payload = {
            "investigation_id": run["id"], "patient_id": scope.patient_id,
            "authorization": {"role": scope.role, "patient_id": scope.patient_id},
            "source_snapshot": fingerprint, "sealed_at": now(), "evidence": sources,
            "decision": None if not decision else {
                "id": decision["id"], "obligation_id": decision["obligation_id"],
                "revision": decision["revision"], "snapshot_hash": decision["snapshot_hash"],
                "rule_key": decision["rule_key"],
                "prerequisites": [{k: p[k] for k in
                    ("id", "category", "definition", "status", "source_refs", "issues")}
                    for p in decision["prerequisites"]],
                "timing": decision["timing"],
                "timing_policy": None if not decision["timing_policy"] else
                    {k: decision["timing_policy"][k] for k in ("id", "version", "status")}},
            "trusted_context": {
                "obligations": [{k: x[k] for k in ("id", "rule_key", "status")} for x in trusted["obligations"]],
                "life_stage_events": [{k: x[k] for k in ("id", "stage", "recorded")} for x in trusted["life_stage_events"]]},
            "truncated": truncated}
        return cls(canonical(payload), digest(payload))

    def read(self):
        payload = json.loads(self.payload_json)
        if digest(payload) != self.context_id:
            raise ValueError("sealed_context_integrity")
        return payload

    def manifest(self):
        data = self.read()
        return {k: data[k] for k in ("investigation_id", "patient_id", "authorization", "source_snapshot", "sealed_at", "truncated")} | {
            "id": self.context_id, "decision": data["decision"],
            "evidence": [{k: x.get(k) for k in
                ("id", "version", "digest", "source", "clinical_time", "event_time", "received",
                 "supersedes", "quality", "excerpt_omitted")} |
                {"excerpt_digest": digest(x["content"]), "excerpt_characters": len(x["content"])}
                for x in data["evidence"]]}

def routing(sealed, objective, a01_trusted=True):
    data = sealed.read()
    evidence = data["evidence"]
    prereqs = (data["decision"] or {}).get("prerequisites", [])
    reconciliation = any(x["quality"]["state"] in {"conflicting", "superseded"} or x.get("supersedes")
                         for x in evidence) or any(p["status"] in {"conflicting", "requires_reconciliation"} for p in prereqs)
    longitudinal = bool(re.search(r"\b(timeline|chronolog\w*|longitudinal|sequence|life.stage|transition)\b", objective, re.I))
    choices = {
        "A02": (reconciliation, "Source conflict or correction lineage requires reconciliation",
                "No potential source conflict or correction lineage"),
        "A03": (bool(evidence) and longitudinal, "Objective explicitly requires longitudinal source chronology",
                "No longitudinal task; source chronology remains available deterministically"),
        "A04": (any(p["status"] in MISSING for p in prereqs), "Configured evidence prerequisite is missing or unavailable",
                "No missing or unavailable configured prerequisite; conflicts belong to reconciliation")}
    return {i: {"selected": bool(enabled and a01_trusted),
                "reason": yes if enabled and a01_trusted else no if a01_trusted
                          else "A01 failed validation or retrieval; no trusted specialist handoff"}
            for i, (enabled, yes, no) in choices.items()}

def specialist_payload(sealed, identifier, objective, handoff):
    data = sealed.read()
    sources = data["evidence"]
    if identifier == "A02":
        selected = {x["id"] for x in sources if x["quality"]["state"] in {"conflicting", "superseded"} or x.get("supersedes")}
        # Include every retrieved link in each relevant correction chain.
        changed = True
        while changed:
            before = set(selected)
            for x in sources:
                if x["id"] in selected or x.get("supersedes") in selected:
                    selected.add(x["id"])
                    if x.get("supersedes"):
                        selected.add(x["supersedes"])
            changed = selected != before
        sources = [x for x in sources if x["id"] in selected]
    elif identifier == "A04":
        refs = {r for p in (data["decision"] or {}).get("prerequisites", []) for r in p["source_refs"]}
        sources = [x for x in sources if x["id"] in refs]
    payload = {"objective": objective, "evidence": sources, "decision": data["decision"],
               "trusted_context": data["trusted_context"], "context_id": sealed.context_id,
               "authorization": data["authorization"], "validated_handoff": handoff}
    return payload, {x["id"] for x in sources}

class RetrievalCache:
    def __init__(self, fingerprint=None):
        self.cache = {}
        self.fingerprint = fingerprint

    def check_scope(self, context):
        with db.engine.begin() as connection:
            scope = authorize(connection, context.role, context.patient_id)
            tooling.synthetic_scope(connection, scope)
            if self.fingerprint and tooling.fingerprint(connection, scope) != self.fingerprint:
                raise ProviderFailure("evidence_changed")

    def execute(self, context, call):
        started = time.perf_counter()
        metadata = {"name": call["name"], "call_id": call["call_id"], "status": "error",
                    "evidence_ids": [], "cached": False, "executed": False, "duration_ms": 0}
        try:
            self.check_scope(context)
            name = call["name"]
            if name not in tooling.TOOLS:
                return tooling.execute(context, call)
            arguments = tooling.TOOLS[name][0].model_validate_json(call["arguments"]).model_dump(mode="json")
            canonical_name = "evidence_detail" if name in {"get_evidence_provenance", "check_evidence_quality"} else name
            key = digest({"role": context.role, "patient": context.patient_id,
                          "snapshot": self.fingerprint, "tool": canonical_name, "arguments": arguments})
            if key in self.cache:
                body, records, prior = copy.deepcopy(self.cache[key])
                metadata = {**prior, "name": name, "call_id": call["call_id"], "cached": True,
                            "executed": False, "cache_origin_tool": prior["name"], "source_duration_ms": 0}
            else:
                body, records, prior = tooling.execute(context, call)
                metadata = {**prior, "cached": False, "executed": True, "source_duration_ms": prior["duration_ms"]}
                self.check_scope(context)
                if prior["status"] == "ok":
                    self.cache[key] = copy.deepcopy((body, records, metadata))
            metadata.update(response_characters=len(canonical(body)),
                            duration_ms=round((time.perf_counter()-started)*1000))
            return body, records, metadata
        except Exception as error:
            code = error.code if isinstance(error, ProviderFailure) else (
                error.detail.get("code", "tool_denied") if isinstance(error, HTTPException) and isinstance(error.detail, dict)
                else "invalid_tool_request")
            metadata.update(error={"code": code}, duration_ms=round((time.perf_counter()-started)*1000))
            return {"error": {"code": code}}, [], metadata

class BoundedProvider:
    def __init__(self, provider):
        self.provider = provider

    def invoke(self, messages, tools, final=False):
        seen = {}
        compact = []
        for message in messages:
            if message.get("type") == "function_call_output":
                output = json.loads(message["output"])
                body = output.get("result")
                if isinstance(body, dict):
                    def project(item):
                        if "normalized" not in item:
                            return item
                        source = projection(item)
                        identity = (source["id"], source["version"], source["digest"])
                        previous = seen.get(identity)
                        if previous == source:
                            return {"evidence_ref": source["id"], "version": source["version"],
                                    "digest": source["digest"], "reused": True}
                        seen[identity] = source
                        return source
                    if "items" in body:
                        body = {**body, "items": [project(x) for x in body["items"]]}
                    elif "normalized" in body:
                        body = project(body)
                    output = {**output, "result": body}
                message = {**message, "output": canonical(output)}
            compact.append(message)
        size = len(canonical(compact))
        if size > LIMITS["context_characters"]:
            error = ProviderFailure("context_budget_exhausted")
            error.not_sent = True
            error.telemetry = {"agent_id": "A01", "attempted": False, "context_characters": size,
                               "model_latency_ms": 0, "error_class": "budget_exhausted"}
            raise error
        return self.provider.invoke(compact, tools, final=final)
