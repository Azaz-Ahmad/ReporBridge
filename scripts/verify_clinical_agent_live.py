"""Three bounded live investigations in disposable PostgreSQL schemas, using synthetic data only."""
import json
import os
from pathlib import Path
import sys
from datetime import datetime
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app import db
from app.main import app
from app.clinical.access import authorize
from app.clinical.gateway import ClinicalRetrieval
from app.clinical.normalize import digest, extract_document
from app.investigation.provider import configuration
from verify_postgres import scratch_schema

report = ROOT / "test-reports" / ("openai-live-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6])
report.mkdir(parents=True)
settings, availability = configuration()
summary = {"api": "responses", "provider": "openai", "model": settings.model,
           "base_url": settings.base_url, "configuration": settings.public(), "runs": []}


def save_report():
    (report / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if availability != "available":
    summary.update(status="BLOCKED", reason=availability, successful_live_runs=0)
    save_report()
    print("Live verification BLOCKED. Provider status", availability, "Report", report)
    sys.exit(2)

# Apply the configured application bounds with small verification ceilings.
os.environ["OPENAI_MAX_AGENT_STEPS"] = str(min(settings.max_steps, 6))
os.environ["OPENAI_MAX_TOOL_CALLS"] = str(min(settings.max_tools, 6))
os.environ["OPENAI_MAX_OUTPUT_TOKENS"] = str(min(settings.output_tokens, 2400))
questions = {
    "complete": "Summarize the exact documented follow-up flag value available in this synthetic patient's observations. Review source facts only.",
    "missing": "Find the synthetic clinical document for this patient's metabolic assessment. Report inaccessible or missing document content and abstain from clinical conclusions.",
    "conflict": "Investigate the synthetic metabolic-assessment observations, including corrected source versions. Identify conflicting values and abstain from resolving them.",
}


def verify_sources(packet):
    values_checked = 0
    try:
        with db.engine.begin() as connection:
            retrieval = ClinicalRetrieval(connection, authorize(connection, "coordinator", "demo-amira"))
            for reference in packet["source_references"]:
                source = retrieval.get(evidence_id=reference["evidence_id"]).evidence
                if (source.patient_id != "demo-amira" or source.digest != reference["digest"]
                        or source.version != reference["version"]):
                    return False, values_checked
            for finding in packet["findings"]:
                for support in finding["supporting_sources"]:
                    result = retrieval.get(evidence_id=support["evidence_id"])
                    if result.evidence.version != support["version"]:
                        return False, values_checked
                    if support["value_key"]:
                        actual = result.evidence.normalized["values"][support["value_key"]]
                        if digest(json.loads(support["value_json"])) != digest(actual):
                            return False, values_checked
                        values_checked += 1
                    if support["excerpt"]:
                        _, parts = extract_document(result.resource)
                        if not any(support["excerpt"] in body for _, body in parts):
                            return False, values_checked
        return True, values_checked
    except (ValueError, KeyError, TypeError):
        return False, values_checked


def clinical_state(api, headers):
    response = api.get("/api/snapshot", headers=headers)
    assert response.status_code == 200
    snapshot = response.json()
    return {key: snapshot[key] for key in ("clinical_obligations", "clinical_approvals", "closure_evidence")}


def run_case(api, headers, case, question):
    before = clinical_state(api, headers)
    response = api.post("/api/v1/agents/clinical-evidence/runs", headers=headers,
        json={"patient_id": "demo-amira", "question": question, "synthetic_only": True,
              "request_id": "live-" + uuid4().hex})
    if response.status_code != 200:
        return {"case": case, "passed": False, "http_status": response.status_code}
    run = response.json()
    detail = run["detail"]
    packet = detail.get("packet")
    path = "/api/v1/agents/clinical-evidence/runs/" + run["id"]
    trace_response = api.get(path + "/trace", headers=headers)
    assert trace_response.status_code == 200
    trace = trace_response.json()
    checks = {
        "model_generated_packet": bool(packet and packet["origin"] == "model"),
        "real_response_metadata": bool(trace.get("model_history")) and all(
            item.get("response_id") and item.get("reported_model")
            and item["requested_model"] == settings.model for item in trace.get("model_history", [])),
        "actual_authorized_tools": bool(detail["tool_history"]) and all(
            item["status"] == "ok" for item in detail["tool_history"]),
        "usage_recorded": detail["usage"]["input_tokens"] > 0 and detail["usage"]["output_tokens"] > 0,
        "grounding_accepted": bool(packet and packet["grounding_status"] != "validation_failed"
                                   and not detail.get("validation", {}).get("errors")),
        "citations_valid": False, "structured_values_valid": False,
        "expected_abstention": False, "human_review_routed": False,
    }
    values_checked = 0
    if packet:
        valid, values_checked = verify_sources(packet)
        checks["citations_valid"] = valid and bool(packet["source_references"])
        checks["structured_values_valid"] = valid and (case == "missing" or values_checked > 0)
        checks["expected_abstention"] = (
            not packet["abstained"] if case == "complete" else
            packet["abstained"] and bool(packet["missing_information"]) if case == "missing" else
            packet["abstained"] and bool(packet["conflicting_evidence"])
            and packet["grounding_status"] == "conflicting_evidence")
        submitted = api.post(path + "/submit", headers=headers)
        reviewer = {"Authorization": "Bearer " + os.environ["REVIEWER_TOKEN"]}
        reviewed_packet = api.get(path + "/review-packet", headers=reviewer)
        checks["human_review_routed"] = (packet["requires_human_review"]
            and submitted.status_code == 200 and submitted.json()["status"] == "pending_review"
            and reviewed_packet.status_code == 200 and reviewed_packet.json() == packet)
    checks["clinical_state_preserved"] = before == clinical_state(api, headers)
    return {"case": case, "passed": all(checks.values()), "run_id": run["id"], "checks": checks,
            "structured_values_checked": values_checked, "packet": packet, "trace": trace}


original_engine = db.engine
try:
    for case, question in questions.items():
        with scratch_schema() as database:
            engine = create_engine(database, pool_pre_ping=True)
            db.engine = engine
            try:
                command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")
                with TestClient(app) as api:
                    headers = {"Authorization": "Bearer " + os.environ["COORDINATOR_TOKEN"]}
                    assert api.post("/api/demo/seed", headers=headers).status_code == 200
                    if case == "conflict":
                        assert api.post("/api/v1/clinical/demo/dataset", headers=headers).status_code == 200
                    if case == "missing":
                        from app.clinical.fixtures import note, TIME
                        response = api.post("/api/v1/clinical/patients/demo-amira/events", headers=headers,
                            json={"source": "synthetic-live-eval", "event_id": "missing-note", "version": 1,
                                  "event_time": TIME, "resource": note("missing-live-eval", "clinical-note")})
                        assert response.status_code == 200
                    result = run_case(api, headers, case, question)
                    summary["runs"].append(result)
                    save_report()
                    print("Live case", case, "PASS" if result["passed"] else "FAIL", flush=True)
            finally:
                engine.dispose()
                db.engine = original_engine
finally:
    db.engine = original_engine
summary["successful_live_runs"] = sum(item["passed"] for item in summary["runs"])
summary["status"] = "PASS" if summary["successful_live_runs"] == 3 else "FAIL"
save_report()
print("Live verification", summary["status"], "Report", report)
sys.exit(0 if summary["status"] == "PASS" else 1)
