"""Record actual synthetic Responses-agent turns, never substitute a test double.
Usage: .venv/Scripts/python.exe scripts/record_demo_llm.py --cases tsp-amira history-amira tsp-uncertain
Each case uses its own temporary migrated SQLite DB, not the running application.
"""
import argparse,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from secrets import token_hex
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases",nargs="+",choices=["tsp-amira","history-amira","tsp-uncertain"],default=["tsp-amira","history-amira"])
    parser.add_argument("--output",default=str(ROOT/"backend/demo-replays"))
    parser.add_argument("--execute",choices=["tsp-amira","history-amira","tsp-uncertain"])
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env")
    if not os.getenv("OPENAI_API_KEY","").strip():
        print(json.dumps({"status":"skipped","reason":"OPENAI_API_KEY is not configured","live_calls":0}));return
    if not os.getenv("OPENAI_MODEL","").strip():raise SystemExit("Set OPENAI_MODEL to an explicitly permitted model before recording.")
    target=Path(args.output).resolve();target.mkdir(parents=True,exist_ok=True)
    if not args.execute:
        results=[]
        for case in args.cases:
            if (target/(("history-" if case.startswith("history") else "tsp-")+("demo-tsp-uncertain" if case.endswith("uncertain") else "demo-amira")+".json")).exists():
                raise SystemExit("Recording exists; select a new output directory to preserve prior live evidence.")
            command=[sys.executable,str(Path(__file__).resolve()),"--execute",case,"--output",str(target)]
            result=subprocess.run(command,cwd=ROOT)
            results.append({"case":case,"exit_code":result.returncode})
        print(json.dumps({"recording_results":results}));raise SystemExit(1 if any(r["exit_code"] for r in results) else 0)
    with tempfile.TemporaryDirectory(prefix="reprobridge-record-") as temporary:
        os.environ.update(DATABASE_URL="sqlite:///"+str(Path(temporary)/"synthetic.db").replace("\\","/"),DEMO_MODE="true",LLM_MODE="live",LLM_RECORD_DIR=str(target),CLINICAL_EVIDENCE_AGENT_ENABLED="true")
        for role in ["COORDINATOR","REVIEWER","VIEWER"]:os.environ[role+"_TOKEN"]=token_hex(32)
        sys.path.insert(0,str(ROOT/"backend"));os.chdir(ROOT/"backend")
        from alembic.config import Config
        from alembic import command
        command.upgrade(Config("alembic.ini"),"head")
        from app.main import app
        from app.investigation import service,provider
        original=service.provider_factory
        def no_retry(settings):
            adapter=original(settings)
            if hasattr(adapter,"inner"):adapter.inner.retry_attempts=1
            return adapter
        service.provider_factory=no_retry
        from fastapi.testclient import TestClient
        headers={"Authorization":"Bearer "+os.environ["COORDINATOR_TOKEN"]}
        with TestClient(app,headers=headers) as client:
            response=client.post("/api/v1/tsp/demo/reset");response.raise_for_status()
            patient="demo-tsp-uncertain" if args.execute.endswith("uncertain") else "demo-amira"
            prefix="/api/v1/tsp"
            if args.execute.startswith("history"):
                client.post("/api/v1/history-handoff/seed").raise_for_status()
                client.post("/api/v1/history-handoff/patients/demo-amira/receive").raise_for_status()
                prefix="/api/v1/history-handoff"
            began=time.perf_counter()
            response=client.post(prefix+"/patients/"+patient+"/investigations",json={"request_id":"live-recording-"+token_hex(8)})
            if response.status_code!=200:
                from app.investigation.replay import scrub
                report={"case":args.execute,"http_status":response.status_code,"error":scrub(response.json()),"latency_ms":round((time.perf_counter()-began)*1000)}
            else:
                run=response.json();d=run["detail"];packet=d.get("packet") or {}
                report={"case":args.execute,"status":run["status"],"model":d["configuration"]["model"],"model_history":d.get("model_history",[]),"latency_ms":round((time.perf_counter()-began)*1000),"usage":d["usage"],"grounding":d.get("validation"),"abstained":packet.get("abstained"),"origin":packet.get("origin"),"error":d.get("error"),"tool_count":len(d.get("tool_history",[]))}
            from app.investigation.replay import scrub
            report=scrub(report);(target/(args.execute+"-result.json")).write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps(report),flush=True)
            if report.get("http_status") or report.get("error") or report.get("origin")!="model":raise SystemExit(1)
if __name__=="__main__":main()
