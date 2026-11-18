"""Three bounded OpenAI investigations in disposable PostgreSQL schemas, using synthetic data only."""
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
from app.investigation.provider import configuration
from verify_postgres import scratch_schema

report = ROOT / "test-reports" / ("openai-live-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
report.mkdir(parents=True, exist_ok=True)
settings, availability = configuration()
summary = {"api": "responses", "provider": "openai", "model": settings.model,
           "base_url": settings.base_url, "runs": []}
if availability != "available":
    summary.update(status="BLOCKED", reason=availability, successful_live_runs=0)
    (report / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Live verification BLOCKED. Provider status", availability, "Report", report)
    sys.exit(2)

# Keep each explicitly requested verification bounded without maintaining a pricing catalog.
os.environ["OPENAI_MAX_AGENT_STEPS"] = str(min(settings.max_steps, 4))
os.environ["OPENAI_MAX_TOOL_CALLS"] = str(min(settings.max_tools, 4))
os.environ["OPENAI_MAX_OUTPUT_TOKENS"] = str(min(settings.output_tokens, 1800))
questions = {
    "complete": "Summarize the exact documented follow-up flag value available in this synthetic patient's observations. Review source facts only.",
    "missing": "Find the synthetic clinical document for this patient's metabolic assessment. Report inaccessible or missing document content and abstain from clinical conclusions.",
    "conflict": "Investigate the synthetic metabolic-assessment observations, including corrected source versions. Identify conflicting values and abstain from resolving them.",
}
original_engine = db.engine
try:
    for case, question in questions.items():
        with scratch_schema() as database:
            engine = create_engine(database, pool_pre_ping=True)
            db.engine = engine
            try:
                command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")
                with TestClient(app) as api:
                    token = os.environ["COORDINATOR_TOKEN"]
                    headers = {"Authorization": "Bearer " + token}
                    assert api.post("/api/demo/seed", headers=headers).status_code == 200
                    if case == "conflict":
                        assert api.post("/api/v1/clinical/demo/dataset", headers=headers).status_code == 200
                    if case == "missing":
                        from app.clinical.fixtures import note, TIME
                        missing = note("missing-live-eval", "clinical-note")
                        response = api.post("/api/v1/clinical/patients/demo-amira/events", headers=headers,
                            json={"source": "synthetic-live-eval", "event_id": "missing-note", "version": 1,
                                  "event_time": TIME, "resource": missing})
                        assert response.status_code == 200
                    result = api.post("/api/v1/agents/clinical-evidence/runs", headers=headers,
                        json={"patient_id": "demo-amira", "question": question, "synthetic_only": True,
                              "request_id": "live-" + uuid4().hex})
                    if result.status_code != 200:
                        summary["runs"].append({"case": case, "passed": False, "http_status": result.status_code})
                        continue
                    run = result.json()
                    detail = run["detail"]
                    packet = detail.get("packet")
                    passed = bool(packet and packet["origin"] == "model" and
                                  detail["usage"]["model_calls"] >= 2 and detail["tool_history"] and
                                  packet["source_references"] and packet["grounding_status"] != "validation_failed")
                    if case == "missing":
                        passed = passed and bool(packet["missing_information"]) and packet["abstained"]
                    if case == "conflict":
                        passed = passed and packet["grounding_status"] == "conflicting_evidence" and packet["abstained"]
                    trace = api.get("/api/v1/agents/clinical-evidence/runs/" + run["id"] + "/trace", headers=headers)
                    assert trace.status_code == 200
                    summary["runs"].append({"case": case, "passed": passed, "run_id": run["id"],
                                            "packet": packet, "trace": trace.json()})
            finally:
                engine.dispose()
                db.engine = original_engine
finally:
    db.engine = original_engine
summary["successful_live_runs"] = sum(item["passed"] for item in summary["runs"])
summary["status"] = "PASS" if summary["successful_live_runs"] == 3 else "FAIL"
(report / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("Live verification", summary["status"], "Report", report)
sys.exit(0 if summary["status"] == "PASS" else 1)
