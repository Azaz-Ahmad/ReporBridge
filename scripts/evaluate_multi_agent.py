"""Repeatable labeled safety and matched-snapshot comparisons; no live model calls."""
import json,os,subprocess,sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
report=ROOT/"test-reports"/("multi-eval-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid4().hex[:6])
report.mkdir()
environment={**os.environ,"MULTI_AGENT_EVAL_DIRECTORY":str(report)}
command=[sys.executable,"-m","pytest","-q","tests/test_multi.py","--tb=short","--basetemp="+str(report/"tmp"),"--junitxml="+str(report/"evaluations.xml")]
result=subprocess.run(command,cwd=ROOT/"backend",env=environment)
cases=[json.loads(p.read_text()) for p in report.glob("*.json")]
summary={"provider":"deterministic_test_double","live":False,"passed":result.returncode==0,"cases":cases,"recorded_cases":len(cases)}
(report/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
print("Synthetic evaluation report",report)
sys.exit(result.returncode)
