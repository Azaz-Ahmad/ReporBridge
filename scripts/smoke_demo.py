"""Budgeted local synthetic demo smoke. No paid provider request is made.
Run against DEMO_MODE=true, REPROBRIDGE_TEST_MODE=true, LLM_MODE=replay.
"""
import argparse,json,os,time,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]


class LocalAPI:
    def __init__(self,url,token,deadline):
        parsed=urlsplit(url)
        if parsed.scheme not in {"http","https"} or parsed.hostname not in {"localhost","127.0.0.1","::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Smoke is restricted to a local synthetic demo URL without embedded credentials.")
        self.url=url.rstrip("/");self.token=token;self.deadline=deadline
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(self,path,body=None):
        remaining=self.deadline-time.monotonic()
        if remaining<=0:raise TimeoutError("60-second smoke budget exhausted")
        request=urllib.request.Request(self.url+"/api"+path,data=json.dumps(body).encode() if body is not None else None,headers={"Authorization":"Bearer "+self.token,"Content-Type":"application/json"})
        with self.opener.open(request,timeout=min(10,remaining)) as response:return json.load(response)


def live_catalog_probe(deadline):
    """Read-only /models reachability, no Responses request and no patient data."""
    import sys
    sys.path.insert(0,str(ROOT/"backend"))
    from app.investigation.provider import Settings, OpenAIProvider
    remaining=deadline-time.monotonic()
    if remaining<1:raise TimeoutError("60-second smoke budget exhausted")
    if not os.getenv("OPENAI_API_KEY","").strip() or not os.getenv("OPENAI_MODEL","").strip():return False
    settings=Settings(model=os.environ["OPENAI_MODEL"],base_url=os.getenv("OPENAI_BASE_URL","") or "https://api.openai.com/v1",timeout=min(10,remaining))
    adapter=OpenAIProvider(settings)
    try:return isinstance(adapter.client.models.list().data,list)
    finally:adapter.close()


def checks(api,live_probe=None):
    results=[]
    def check(name,action):
        try:
            ok=bool(action());results.append({"check":name,"passed":ok})
        except Exception as error:results.append({"check":name,"passed":False,"error":type(error).__name__})
    check("Backend ready and migration at head",lambda:api.call("/health")["status"]=="ready")
    check("Synthetic coordinator demo session",lambda:(lambda s:s.get("demo_mode") and s.get("role")=="coordinator")(api.call("/session")))
    if not all(r["passed"] for r in results):return results
    check("Confirmed synthetic reset / default date",lambda:api.call("/v1/tsp/demo/reset",{})["clock"]["as_of"]=="2026-11-22")
    check("Amira IN_WINDOW",lambda:api.call("/v1/tsp/patients/demo-amira/window")["status"]=="IN_WINDOW")
    check("Uncertain dating on hold",lambda:api.call("/v1/tsp/patients/demo-tsp-uncertain/window")["status"]=="HOLD_DATING_UNCERTAIN")
    status={}
    def provider_status():
        status.update(api.call("/v1/agents/clinical-evidence/status"))
        return status.get("modes",{}).get("live",{}).get("available",False)
    check("Live adapter configured (no paid request; auth evidence is the live recording report)",provider_status)
    if live_probe is not None:check("Live API catalog reachable (read-only; no generation)",live_probe)
    check("Replay adapter configured",lambda:status.get("modes",{}).get("replay",{}).get("available",False))
    if status.get("llm_mode")!="replay":
        results.append({"check":"Replay is the active demo mode; restart with LLM_MODE=replay","passed":False});return results
    replay_metrics={}
    def explanation(patient):
        run=api.call("/v1/tsp/patients/"+patient+"/investigations",{"request_id":"smoke-"+str(time.time_ns())})
        detail=run["detail"];packet=detail.get("packet") or {}
        replay_metrics[patient]={"error":detail.get("error"),"validation":detail.get("validation"),"origin":packet.get("origin"),"live_model_calls":detail["usage"]["model_calls"]}
        return detail["usage"]["model_calls"]==0 and packet.get("origin")=="model" and packet.get("grounding_status")!="validation_failed" and not detail.get("error")
    check("Amira real-recorded replay explanation accepted",lambda:explanation("demo-amira"))
    results[-1]["detail"]=replay_metrics.get("demo-amira")
    check("Uncertain real-recorded replay explanation accepted",lambda:explanation("demo-tsp-uncertain"))
    results[-1]["detail"]=replay_metrics.get("demo-tsp-uncertain")
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--base-url",default="http://127.0.0.1:8000");parser.add_argument("--report")
    args=parser.parse_args();from dotenv import load_dotenv
    load_dotenv(ROOT/".env");began=time.monotonic()
    try:result=checks(LocalAPI(args.base_url,os.getenv("COORDINATOR_TOKEN",""),began+60),lambda:live_catalog_probe(began+60))
    except Exception as error:result=[{"check":"Local smoke setup","passed":False,"error":type(error).__name__}]
    for item in result:print(("PASS " if item["passed"] else "FAIL ")+item["check"]+(" ("+item["error"]+")" if item.get("error") else ""))
    report={"checks":result,"duration_ms":round((time.monotonic()-began)*1000),"live_generation_requests":0,"live_catalog_probe":True,"passed":all(r["passed"] for r in result)}
    if args.report:Path(args.report).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Smoke elapsed: "+str(report["duration_ms"])+" ms; paid requests: 0")
    raise SystemExit(0 if report["passed"] else 1)
if __name__=="__main__":main()
