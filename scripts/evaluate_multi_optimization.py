"""Labeled matched-snapshot optimization safety comparisons. No live requests."""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4
ROOT = Path(__file__).resolve().parents[1]
report = ROOT / "test-reports" / ("i21-eval-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6])
report.mkdir()
environment = {**os.environ, "MULTI_OPT_EVAL_DIRECTORY": str(report)}
result = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_multi_optimization.py",
    "--tb=short", "--basetemp=" + str(report / "tmp"), "--junitxml=" + str(report / "evaluations.xml")],
    cwd=ROOT / "backend", env=environment)
cases = [json.loads(p.read_text()) for p in report.glob("*.json")]
summary = {"provider": "deterministic_test_double", "live": False,
           "passed": result.returncode == 0, "recorded_matched_cases": len(cases), "cases": cases}
(report / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("Optimization safety report", report)
sys.exit(result.returncode)
