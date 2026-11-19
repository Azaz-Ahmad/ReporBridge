"""Export actual trace fields and matched metrics, leaving unavailable historical measurements blank."""
import argparse
import csv
import json
import statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("report", type=Path)
parser.add_argument("--publish-trace", action="store_true")
args = parser.parse_args()
report = args.report.resolve()
report.relative_to(ROOT / "test-reports")
data = json.loads((report / "summary.json").read_text(encoding="utf-8"))
rows = []
def steps(case, profile, repetition, run, invocations=None):
    detail = run["detail"]
    agents = detail["multi_agent"]["agents"]
    models = invocations if invocations is not None else detail["model_history"]
    requests = {call["call_id"]: index+1 for index, model in enumerate(models) for call in model.get("requested_tools", [])}
    for index, model in enumerate(models):
        identifier = model.get("agent_id", "A01")
        rows.append({"case": case, "profile": profile, "repetition": repetition, "run_id": run["id"],
            "step_type": "provider_invocation", "agent": identifier, "call_number": index+1,
            "tool": ";".join(x["name"] for x in model.get("requested_tools", [])),
            "input_tokens": model.get("input_tokens"), "output_tokens": model.get("output_tokens"),
            "model_latency_ms": model.get("model_latency_ms"), "tool_latency_ms": None,
            "context_characters": model.get("context_characters"), "schema_characters": model.get("schema_characters"),
            "input_evidence_refs": ";".join(x["id"] for x in model.get("input_evidence_references", [])),
            "input_refs_recorded": "input_evidence_references" in model,
            "tool_purpose": "", "cached": None,
            "agent_final_evidence_refs": ";".join(agents[identifier]["supporting_evidence_refs"]),
            "retries": model.get("retries"), "error_class": model.get("error_class", model.get("error")),
            "agent_grounding": agents[identifier]["validation_status"],
            "requested_model": model.get("requested_model"), "reported_model": model.get("reported_model"),
            "response_id": model.get("response_id")})
    for tool in detail["tool_history"]:
        rows.append({"case": case, "profile": profile, "repetition": repetition, "run_id": run["id"],
            "step_type": "tool", "agent": "A01", "call_number": requests.get(tool["call_id"]), "tool": tool["name"],
            "input_tokens": None, "output_tokens": None, "model_latency_ms": None,
            "tool_latency_ms": tool["duration_ms"], "context_characters": tool.get("response_characters"),
            "schema_characters": None, "input_evidence_refs": ";".join(tool["evidence_ids"]),
            "agent_final_evidence_refs": "", "input_refs_recorded": True,
            "tool_purpose": tool.get("purpose", "model_selected"), "cached": tool.get("cached", False),
            "retries": None, "error_class": (tool.get("error") or {}).get("code"),
            "agent_grounding": detail["validation"]["status"] if tool["status"] == "ok" else None,
            "requested_model": "", "reported_model": "", "response_id": ""})
for result in data["runs"]:
    steps(result["case"], result["profile"] + ("-parallel" if result["case"] == "parallel_chronology" and result["parallel"] else
          "-serial" if result["case"] == "parallel_chronology" else ""), result["repetition"], result["run"], result["provider_invocations"])
history = ROOT / "test-reports/multi-live-20261119-230124-e75d21/summary.json"
if history.exists():
    for case in json.loads(history.read_text())["cases"]:
        steps(case["case"], "historical-increment-2", 1, case["multi"]["run"])
retained = ROOT / 'test-reports/i21-retained-live.json'
if retained.exists():
    proof = json.loads(retained.read_text())
    steps('full_m08_ui', 'optimized-retained', 1, proof['run'])
fields = list(rows[0])
for destination in [report / "steps.csv", *([ROOT / "docs/V06_I21_TRACE_ANALYSIS.csv"] if args.publish_trace else [])]:
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
metrics = {}
for case in ("complete", "conflicting", "missing_prerequisite"):
    metrics[case] = {}
    for profile in ("legacy", "optimized"):
        runs = [x for x in data["runs"] if x["case"] == case and x["profile"] == profile]
        details = [x["run"]["detail"] for x in runs]
        metrics[case][profile] = {"runs": len(runs), "passed": sum(x["passed"] for x in runs),
            "model_calls_mean": statistics.mean(x["usage"]["model_calls"] for x in details),
            "tool_calls_mean": statistics.mean(sum(not t.get("cached") and t.get("executed", True) for t in x["tool_history"]) for x in details),
            "input_tokens_mean": statistics.mean(x["usage"]["input_tokens"] for x in details),
            "output_tokens_mean": statistics.mean(x["usage"]["output_tokens"] for x in details),
            "latency_ms_mean": statistics.mean(x["duration_ms"] for x in details),
            "latency_ms_range": [min(x["duration_ms"] for x in details), max(x["duration_ms"] for x in details)]}
base = sum(x["legacy"]["input_tokens_mean"] for x in metrics.values())
optimized = sum(x["optimized"]["input_tokens_mean"] for x in metrics.values())
conflict = metrics["conflicting"]
metrics["targets"] = {"aggregate_input_reduction_percent": 100*(base-optimized)/base,
    "conflict_latency_reduction_percent": 100*(conflict["legacy"]["latency_ms_mean"]-conflict["optimized"]["latency_ms_mean"])/conflict["legacy"]["latency_ms_mean"],
    "all_primary_runs_passed": all(x["passed"] for x in data["runs"] if x["case"] != "parallel_chronology")}
parallel = [x for x in data["runs"] if x["case"] == "parallel_chronology"]
if parallel:
    serial = statistics.mean(x["run"]["detail"]["duration_ms"] for x in parallel if not x["parallel"])
    concurrent = statistics.mean(x["run"]["detail"]["duration_ms"] for x in parallel if x["parallel"])
    metrics["parallel_comparison"] = {"serial_mean_ms": serial, "parallel_mean_ms": concurrent,
        "latency_reduction_percent": 100*(serial-concurrent)/serial, "all_passed": all(x["passed"] for x in parallel)}
(report / "analysis.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(json.dumps(metrics, indent=2))
