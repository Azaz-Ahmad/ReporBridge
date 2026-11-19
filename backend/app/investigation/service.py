"""Durable run reservation and review, independent of clinical closure records."""
import time
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import select

from app import db
from app.clinical.access import authorize, audit_access, fail, now
from app.clinical.normalize import digest
from app.investigation import provider, tooling
from app.investigation.graph import SYSTEM, build
from app.investigation.schema_v1 import runs, reviews
from app.prevention.window_grounding import prompt as window_prompt


def provider_factory(settings):
    return provider.OpenAIProvider(settings)


def status():
    settings, availability = provider.configuration()
    return {"provider": "openai", "api": "responses", "status": availability,
            "available": availability == "available", "configuration": settings.public(),
            "synthetic_only": True, "live_verification": "requires_actual_api_run"}


def get(connection, actor, run_id):
    run = connection.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
    if not run:
        fail(404, "run_unavailable", "Investigation unavailable in this scope.")
    authorize(connection, actor, run["patient_id"])
    result = dict(run)
    result["review"] = connection.execute(select(reviews).where(
        reviews.c.run_id == run_id)).mappings().first()
    if result["review"]:
        result["review"] = dict(result["review"])
    return result


def reserve(connection, actor, request, settings, availability, binding=None, workflow='single_agent', window_context=None):
    context = authorize(connection, actor, request.patient_id)
    tooling.synthetic_scope(connection, context)
    existing = connection.execute(select(runs).where(
        runs.c.actor == actor, runs.c.patient_id == request.patient_id,
        runs.c.request_id == request.request_id)).mappings().first()
    fingerprint = digest({"patient_id": request.patient_id, "question": request.question,
                          **({"decision_context": binding} if binding else {}),
                          **({"window_context": window_context} if window_context else {}),
                          **({"workflow": workflow} if workflow != "single_agent" else {})})
    if existing:
        if existing["fingerprint"] != fingerprint:
            fail(409, "idempotency_conflict", "Request ID already belongs to a different question.")
        return get(connection, actor, existing["id"]), False, None
    if availability != "available":
        fail(503, "provider_unavailable", "Clinical Evidence Agent unavailable. Provider status is " + availability + ".")
    stamp = now()
    run = {"id": "investigation-" + uuid4().hex, "patient_id": request.patient_id,
           "actor": actor, "request_id": request.request_id, "fingerprint": fingerprint,
           "status": "running", "created": stamp, "updated": stamp,
           "detail": {"question": request.question, "configuration": settings.public(),
                      "provider": "openai", "api": "responses", "trace": [], "tool_history": [],
                      "evidence_references": [], "packet": None, "error": None,
                      "usage": {"model_calls": 0, "input_tokens": 0, "output_tokens": 0,
                                "retries": 0, "usage_complete": True}, "duration_ms": 0,
                      "submitted": False, "source_snapshot": tooling.fingerprint(connection, context),
                      "decision_context": binding, "window_context": window_context, "workflow": workflow}}
    connection.execute(runs.insert().values(**run))
    audit_access(connection, context, "investigation_started")
    return run, True, tooling.fingerprint(connection, context)


def save(connection, actor, run_id, state, elapsed, extra_detail=None):
    run = get(connection, actor, run_id)
    if run["status"] != "running":
        fail(409, "run_interrupted", "This run can no longer publish a result.")
    detail = {**run["detail"], "trace": state.get("trace", []),
              "tool_history": state.get("tool_history", []),
              "model_history": state.get("model_history", []),
              "denied_tool_requests": state.get("denied_tool_requests", []),
              "usage": state.get("usage", run["detail"]["usage"]),
              "error": state.get("error"), "duration_ms": elapsed,
              "validation": state.get("validation"),
              "packet": state.get("packet"),
              "evidence_references": [
                  {"id": item["id"], "version": item["version"], "digest": item["digest"],
                   "quality": item["quality"]["state"]}
                  for item in {row["id"]: row for row in state.get("evidence", [])}.values()],
              **(extra_detail or {})}
    connection.execute(runs.update().where(runs.c.id == run_id).values(
        status=state.get("status", "running"), updated=now(), detail=detail))


def run_investigation(actor, request, write, trusted_decision=None, trusted_window=None):
    settings, availability = provider.configuration()
    run, created, fingerprint = write(reserve, actor, request, settings, availability, trusted_decision, "single_agent", trusted_window)
    if not created:
        return run
    # Re-authorize after reservation so no model chooses its trusted scope.
    with db.engine.begin() as connection:
        context = authorize(connection, actor, request.patient_id)
    state = {
        "run_id": run["id"], "patient_id": context.patient_id, "actor": actor,
        "question": request.question, "allowed_tools": list(tooling.TOOLS),
        "messages": [{"role": "system", "content": SYSTEM + (window_prompt(trusted_window) if trusted_window else "")},
                     {"role": "user", "content": request.question}],
        "calls": [], "tool_history": [], "evidence": [], "draft": None,
        "status": "running", "error": None, "steps": 0, "trace": [],
        "usage": run["detail"]["usage"]}
    started = time.perf_counter()

    def persist(current, elapsed):
        write(save, actor, run["id"], current, elapsed)

    model_provider = None
    try:
        model_provider = provider_factory(settings)
        graph = build(model_provider, settings, run, context, persist, fingerprint)
        graph.invoke(state, config={"recursion_limit": 2 * settings.max_steps + 12})
    except Exception:
        # Persist failure after interruption/provider initialization failure without raw exception text.
        with db.engine.begin() as connection:
            saved = get(connection, actor, run["id"])
        if saved["status"] == "running":
            detail = {**saved["detail"], "error": "investigation_interrupted",
                      "duration_ms": round((time.perf_counter() - started) * 1000)}
            write(mark_failure, actor, run["id"], detail)
    finally:
        if model_provider is not None and callable(getattr(model_provider, "close", None)):
            model_provider.close()
    with db.engine.begin() as connection:
        return get(connection, actor, run["id"])


def mark_failure(connection, actor, run_id, detail):
    run = get(connection, actor, run_id)
    if run["status"] == "running":
        if detail.get("multi_agent"):
            multi = dict(detail["multi_agent"])
            agents = {identifier: dict(record) for identifier, record in multi["agents"].items()}
            for record in agents.values():
                if record["state"] in {"pending", "running"}:
                    record.update(state="failed", error="worker_interrupted", abstained=True)
                    record["execution_metadata"] = {**record["execution_metadata"], "finished": now(), "error_class": "interrupted"}
            multi.update(agents=agents, reserved_specialist_calls=0)
            detail = {**detail, "multi_agent": multi, "usage": {**detail["usage"], "usage_complete": False}}
        connection.execute(runs.update().where(runs.c.id == run_id).values(
            status="interrupted", updated=now(), detail=detail))


def fetch(connection, actor, run_id):
    run = get(connection, actor, run_id)
    age = (datetime.now(UTC) - datetime.fromisoformat(run["updated"])).total_seconds()
    if run["status"] == "running" and age > 240:
        mark_failure(connection, actor, run_id, {**run["detail"], "error": "worker_interrupted"})
        run = get(connection, actor, run_id)
    audit_access(connection, authorize(connection, actor, run["patient_id"]), "investigation_read")
    return run


def list_runs(connection, actor, patient_id):
    authorize(connection, actor, patient_id)
    return [get(connection, actor, identifier) for identifier in connection.execute(
        select(runs.c.id).where(runs.c.patient_id == patient_id).order_by(runs.c.created.desc()).limit(20)).scalars()]


def sources_current(connection, actor, run):
    window = run["detail"].get("window_context")
    if window:
        from app.prevention.window_grounding import current
        if not current(connection, actor, window):
            fail(409, "stale_review_packet", "Prevention window context changed. Start a fresh investigation.")
    scope = authorize(connection, actor, run["patient_id"])
    tooling.synthetic_scope(connection, scope)
    retrieval = tooling.ClinicalTools(connection, scope).retrieval
    binding = run["detail"].get("decision_context")
    if binding:
        from app.prevention.service import validate_binding
        if not validate_binding(connection, binding):
            fail(409, "stale_review_packet", "Decision context changed. Start a fresh investigation.")
    if tooling.fingerprint(connection, scope) != run["detail"]["source_snapshot"]:
        fail(409, "stale_review_packet", "Evidence changed. Start a fresh investigation.")
    for item in run["detail"]["evidence_references"]:
        current = retrieval.get(evidence_id=item["id"]).evidence
        if (current.digest != item["digest"] or current.version != item["version"]
                or current.quality["state"] != item["quality"]):
            fail(409, "stale_review_packet", "Evidence changed. Start a fresh investigation.")


def submit(connection, actor, run_id):
    run = get(connection, actor, run_id)
    if not run["detail"].get("packet") or run["status"] in {"running", "interrupted"}:
        fail(409, "packet_unavailable", "A finished review packet is required.")
    if run["review"]:
        return run
    sources_current(connection, actor, run)
    detail = {**run["detail"], "submitted": True}
    connection.execute(runs.update().where(runs.c.id == run_id).values(
        status="pending_review", detail=detail, updated=now()))
    audit_access(connection, authorize(connection, actor, run["patient_id"]), "investigation_submitted")
    return get(connection, actor, run_id)


def review(connection, actor, run_id, request):
    run = get(connection, actor, run_id)
    if run["review"]:
        if run["review"]["decision"] == request.decision and run["review"]["note"] == request.note:
            return run
        fail(409, "review_already_recorded", "This summary already has an immutable review.")
    if run["status"] != "pending_review":
        fail(409, "not_submitted", "Submit the investigation for human review first.")
    sources_current(connection, actor, run)
    packet = run["detail"]["packet"]
    if request.decision == "approve_summary" and (packet["origin"] != "model"
            or packet["grounding_status"] == "validation_failed"
            or packet.get("packet_complete") is False):
        fail(409, "summary_unapprovable", "This abstention or failed validation requires evidence follow-up.")
    connection.execute(reviews.insert().values(run_id=run_id, actor=actor, recorded=now(),
                                               decision=request.decision, note=request.note))
    connection.execute(runs.update().where(runs.c.id == run_id).values(status="reviewed", updated=now()))
    audit_access(connection, authorize(connection, actor, run["patient_id"]), "investigation_summary_reviewed")
    return get(connection, actor, run_id)
