"""Two counterbalanced live repetitions per primary case, on identical pinned synthetic snapshots."""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app import db
from app.main import app
from app.investigation import provider, service, tooling
from app.clinical.access import authorize
from app.clinical.fixtures import TIME, note, resource, coding
from app.clinical.gateway import ClinicalRetrieval
from app.clinical.normalize import digest, extract_document
from app.multi.telemetry import MeasuredProvider
from verify_postgres import scratch_schema

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repetitions", type=int, choices=(1, 2), default=2)
parser.add_argument("--parallel-comparison", action="store_true")
args = parser.parse_args()
report = ROOT / "test-reports" / ("i21-live-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6])
report.mkdir()
summary = {"live": True, "baseline_commit": "da44aea61ea2bf5aabae621b5735ab42fef8f348",
           "repetitions": args.repetitions, "runs": [], "status": "RUNNING"}
def save():
    (report / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
os.environ["OPENAI_MAX_OUTPUT_TOKENS"] = "4000"
os.environ["MULTI_AGENT_MAX_OUTPUT_TOKENS"] = "4000"
os.environ["OPENAI_REASONING_EFFORT"] = "low"
os.environ["MULTI_AGENT_REASONING_EFFORT"] = "low"
settings, availability = provider.configuration()
summary.update(provider_status=availability, configuration=settings.public())
save()
if availability != "available":
    summary["status"] = "BLOCKED"; save()
    print("Live verification BLOCKED:", availability, "Report", report); sys.exit(2)
original_engine, original_factory = db.engine, service.provider_factory
headers = {"Authorization": "Bearer " + os.environ["COORDINATOR_TOKEN"]}
objective = ("Review synthetic metabolic-assessment observations and assessment-summary documents using context and document search. "
    "Cite exact tool item.id/version with exact value_key/value_json or excerpts. State conflicts and abstain if unresolved. "
    "Explain the documented evidence for clinician review. Do not infer clinical completion. "
    "Return at most two findings with one supporting source each, a short summary and short uncertainty/actions. "
    "Prefer one exact structured value and one brief document excerpt.")

def evaluate(api, case, profile, repetition, parallel, expected_snapshot):
    os.environ["MULTI_AGENT_EXECUTION_PROFILE"] = profile
    os.environ["MULTI_AGENT_PARALLEL"] = str(parallel).lower()
    domain = api.get("/api/v1/prevention/snapshot", headers=headers).json()
    linked = next(x for x in domain["decisions"] if x["patient_id"] == "demo-amira" and not x["archived"])
    before = api.get("/api/snapshot", headers=headers).json()
    observations = []
    service.provider_factory = lambda cfg: MeasuredProvider(original_factory(cfg), cfg, observations=observations)
    question = objective if case != "parallel_chronology" else objective + " Explain the longitudinal chronology and correction sequence."
    began = time.perf_counter()
    response = api.post("/api/v1/agents/clinical-evidence/runs/multi-agent", headers=headers, json={
        "patient_id": "demo-amira", "decision_id": linked["id"], "question": question,
        "request_id": "i21-" + uuid4().hex, "synthetic_only": True})
    wall_ms = round((time.perf_counter()-began)*1000)
    service.provider_factory = original_factory
    result = {"case": case, "profile": profile, "repetition": repetition, "parallel": parallel,
              "http_status": response.status_code, "http_latency_ms": wall_ms, "source_snapshot": expected_snapshot}
    if response.status_code != 200:
        result.update(passed=False, error=response.json()); return result
    run = response.json(); detail = run["detail"]; packet = detail.get("packet")
    with db.engine.begin() as c:
        unchanged = tooling.fingerprint(c, authorize(c, "coordinator", "demo-amira")) == expected_snapshot
        retrieval = ClinicalRetrieval(c, authorize(c, "coordinator", "demo-amira"))
        citations = bool(packet and packet["source_references"]); values = 0
        if packet:
            for ref in packet["source_references"]:
                actual = retrieval.get(evidence_id=ref["evidence_id"]).evidence
                citations &= actual.patient_id == "demo-amira" and actual.version == ref["version"] and actual.digest == ref["digest"]
            for finding in packet["findings"]:
                for support in finding["supporting_sources"]:
                    actual = retrieval.get(evidence_id=support["evidence_id"])
                    citations &= actual.evidence.version == support["version"]
                    if support["value_key"]:
                        citations &= digest(json.loads(support["value_json"])) == digest(actual.evidence.normalized["values"][support["value_key"]])
                        values += 1
                    if support["excerpt"]:
                        _, parts = extract_document(actual.resource)
                        citations &= any(support["excerpt"] in text for _, text in parts)
    submitted = api.post("/api/v1/agents/clinical-evidence/runs/" + run["id"] + "/submit", headers=headers)
    agents = detail.get("multi_agent", {}).get("agents", {})
    checks = {
        "real_responses": bool(observations) and all(x.get("response_id") and x.get("reported_model") for x in observations),
        "model_unchanged": all(x["requested_model"] == settings.model for x in observations),
        "source_snapshot_unchanged": unchanged,
        "source_citations_and_values": bool(citations) and values > 0,
        "clinical_state_preserved": before == api.get("/api/snapshot", headers=headers).json(),
        "grounding_accepted": bool(packet and packet["grounding_status"] != "validation_failed") and not (detail.get("validation") or {}).get("errors"),
        "packet_complete": bool(packet and packet["packet_complete"]),
        "no_failed_agents": all(x["state"] != "failed" for x in agents.values()),
        "appropriate_abstention": bool(packet) and (not packet["abstained"] if case == "complete" else packet["abstained"]),
        "human_review": bool(packet and packet["requires_human_review"]) and submitted.status_code == 200 and submitted.json()["status"] == "pending_review",
        "actual_m08_tools": any(not x.get("cached") and x["status"] == "ok" for x in detail["tool_history"])}
    if case == "missing_prerequisite":
        checks["missing_prerequisite"] = bool(packet and packet["missing_information"])
    if case in {"conflicting", "parallel_chronology"}:
        checks["conflict_detection"] = bool(packet and packet["conflicting_evidence"])
    observations.sort(key=lambda x: x["started_at"])
    result.update(run=run, checks=checks, passed=all(checks.values()),
                  provider_invocations=[{**x, "invocation_number": n+1} for n, x in enumerate(observations)],
                  structured_values_checked=values)
    return result

try:
    cases = ["complete", "conflicting", "missing_prerequisite"]
    if args.parallel_comparison:
        cases.append("parallel_chronology")
    for case in cases:
        with scratch_schema() as database:
            db.engine = create_engine(database, pool_pre_ping=True)
            command.upgrade(Config(str(ROOT / "backend/alembic.ini")), "head")
            try:
                with TestClient(app) as api:
                    assert api.post("/api/demo/seed", headers=headers).status_code == 200
                    def ingest(record, event, version=1):
                        response = api.post("/api/v1/clinical/patients/demo-amira/events", headers=headers,
                            json={"source": "synthetic-i2-eval", "event_id": event, "event_time": TIME, "version": version, "resource": record})
                        assert response.status_code == 200, response.text
                    assessment = resource("Observation", "i2-assessment", status="final", code=coding("metabolic-assessment"),
                                          effectiveDateTime=TIME, valueString="Illustrative assessment documentation available for clinician review")
                    ingest(assessment, "assessment")
                    if case != "missing_prerequisite":
                        ingest(note("i2-summary", "assessment-summary",
                                    "# Assessment\nIllustrative assessment documentation available for clinician review."), "summary")
                    if case in {"conflicting", "parallel_chronology"}:
                        ingest(resource("Observation", "i2-conflict", status="final", code=coding("metabolic-assessment"),
                                        effectiveDateTime=TIME, valueString="Illustrative conflicting assessment documentation"), "conflict")
                    if case == "parallel_chronology":
                        ingest({**assessment, "valueString": "Illustrative corrected assessment; clinician reconciliation remains outstanding"},
                               "correction", version=2)
                    with db.engine.begin() as c:
                        pinned = tooling.fingerprint(c, authorize(c, "coordinator", "demo-amira"))
                    for repetition in range(args.repetitions):
                        modes = [("legacy", False), ("optimized", True)] if repetition % 2 == 0 else [("optimized", True), ("legacy", False)]
                        if case == "parallel_chronology":
                            modes = [("optimized", False), ("optimized", True)] if repetition % 2 == 0 else [("optimized", True), ("optimized", False)]
                        for profile, parallel in modes:
                            result = evaluate(api, case, profile, repetition+1, parallel, pinned)
                            summary["runs"].append(result); save()
                            detail = result.get("run", {}).get("detail", {})
                            print(case, profile, "parallel="+str(parallel), "rep="+str(repetition+1),
                                  json.dumps({"passed": result["passed"], "checks": result.get("checks"),
                                              "usage": detail.get("usage"), "latency_ms": detail.get("duration_ms")}), flush=True)
            finally:
                db.engine.dispose(); db.engine = original_engine
    summary["status"] = "PASS" if all(x["passed"] for x in summary["runs"]) else "FAIL"
except BaseException as error:
    summary.update(status="INTERRUPTED", error_class=type(error).__name__)
    raise
finally:
    db.engine = original_engine
    service.provider_factory = original_factory
    save()
print("Live report", report, summary["status"], flush=True)
sys.exit(0 if summary["status"] == "PASS" else 1)
