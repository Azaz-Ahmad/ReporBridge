"""Repeatable deterministic synthetic evaluation. No OpenAI network requests."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
report = ROOT / "test-reports" / ("agent-eval-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8])
report.mkdir(parents=True)
environment = {**os.environ, "CLINICAL_AGENT_EVAL_DIRECTORY": str(report)}
result = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_investigation.py",
                         "--tb=short", "--basetemp=" + str(report / "tmp"),
                         "--junitxml=" + str(report / "evaluations.xml")],
                        cwd=ROOT / "backend", env=environment)
cases = [json.loads(file.read_text(encoding="utf-8")) for file in report.glob("*.json")]
summary = {"provider": "deterministic_test_double", "live_openai": False,
           "cases": cases, "passed": result.returncode == 0,
           "recorded_cases": len(cases), "live_verification": "BLOCKED unless configured and separately executed"}
(report / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("Synthetic evaluation report", report)
sys.exit(result.returncode)
