"""Matched live Responses comparisons using disposable, identical PostgreSQL evidence snapshots."""
import json, os, sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from app import db
from app.main import app, write
from app.investigation import provider, service, tooling
from app.investigation.contracts import RunRequest
from app.clinical.access import authorize
from app.clinical.fixtures import TIME, note, resource, coding
from app.prevention import service as prevention
from app.prevention.contracts import InvestigationRequest
from verify_postgres import scratch_schema
report=ROOT/"test-reports"/("multi-live-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid4().hex[:6])
report.mkdir()
os.environ["OPENAI_MAX_OUTPUT_TOKENS"]="4000"
os.environ["MULTI_AGENT_MAX_OUTPUT_TOKENS"]="4000"
os.environ["OPENAI_REASONING_EFFORT"]="low"
os.environ["MULTI_AGENT_REASONING_EFFORT"]="low"
settings,availability=provider.configuration()
summary={"provider_status":availability,"requested_model":settings.model,"live":True,"cases":[],"status":"RUNNING"}
def save():
 (report/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
save()
if availability!="available":
 summary["status"]="BLOCKED"; save(); sys.exit(2)
original=db.engine
headers={"Authorization":"Bearer "+os.environ["COORDINATOR_TOKEN"]}
for case in ["complete","conflicting","missing_prerequisite"]:
 with scratch_schema() as database:
  db.engine=create_engine(database,pool_pre_ping=True)
  try:
   command.upgrade(Config(str(ROOT/"backend/alembic.ini")),"head")
   with TestClient(app) as api:
    assert api.post("/api/demo/seed",headers=headers).status_code==200
    def ingest(record,event):
     r=api.post("/api/v1/clinical/patients/demo-amira/events",headers=headers,json={"source":"synthetic-i2-eval","event_id":event,"event_time":TIME,"version":1,"resource":record})
     assert r.status_code==200,r.text
    ingest(resource("Observation","i2-assessment",status="final",code=coding("metabolic-assessment"),effectiveDateTime=TIME,valueString="Illustrative assessment documentation available for clinician review"),"assessment")
    if case!="missing_prerequisite":
     ingest(note("i2-summary","assessment-summary","# Assessment\nIllustrative assessment documentation available for clinician review."),"summary")
    if case=="conflicting":
     ingest(resource("Observation","i2-conflict",status="final",code=coding("metabolic-assessment"),effectiveDateTime=TIME,valueString="Illustrative conflicting assessment documentation"),"conflict")
    domain=api.get("/api/v1/prevention/snapshot",headers=headers).json()
    decision=next(x for x in domain["decisions"] if x["patient_id"]=="demo-amira" and not x["archived"])
    objective=("Review synthetic metabolic-assessment observations and assessment-summary documents using context and document search. "
       "Cite exact tool item.id/version with exact value_key/value_json or excerpts. State conflicts and abstain if unresolved. "
       "Explain the documented evidence for clinician review. Do not infer clinical completion. "
       "Return at most two findings with one supporting source each, a short summary and short uncertainty/actions. Prefer one exact structured value and one brief document excerpt.")
    before=api.get("/api/snapshot",headers=headers).json()
    with db.engine.begin() as c:
     fingerprint=tooling.fingerprint(c,authorize(c,"coordinator","demo-amira"))
    binding=write(prevention.prepare_investigation,"coordinator",decision["id"],InvestigationRequest(request_id="binding"))["binding"]
    single=service.run_investigation("coordinator",RunRequest(patient_id="demo-amira",question=objective,request_id="single-"+uuid4().hex,synthetic_only=True),write,trusted_decision=binding)
    response=api.post("/api/v1/agents/clinical-evidence/runs/multi-agent",headers=headers,json={"patient_id":"demo-amira","decision_id":decision["id"],"question":objective,"request_id":"multi-"+uuid4().hex,"synthetic_only":True})
    assert response.status_code==200,response.text
    multi=response.json()
    after=api.get("/api/snapshot",headers=headers).json()
    with db.engine.begin() as c:
     unchanged=fingerprint==tooling.fingerprint(c,authorize(c,"coordinator","demo-amira"))
    records={}
    for mode,run in [("single",single),("multi",multi)]:
     path="/api/v1/agents/clinical-evidence/runs/"+run["id"]
     submitted=api.post(path+"/submit",headers=headers)
     detail=run["detail"]; packet=detail.get("packet")
     agents=detail.get("multi_agent",{}).get("agents",{})
     sources_valid=bool(packet and packet["source_references"])
     from app.clinical.gateway import ClinicalRetrieval
     from app.clinical.normalize import digest,extract_document
     checked_values=0
     with db.engine.begin() as c:
      retrieval=ClinicalRetrieval(c,authorize(c,"coordinator","demo-amira"))
      for ref in (packet or {}).get("source_references",[]):
       source=retrieval.get(evidence_id=ref["evidence_id"]).evidence
       sources_valid &= source.patient_id=="demo-amira" and source.version==ref["version"] and source.digest==ref["digest"]
      for finding in (packet or {}).get("findings",[]):
       for support in finding["supporting_sources"]:
        result=retrieval.get(evidence_id=support["evidence_id"])
        sources_valid &= result.evidence.version==support["version"]
        if support["value_key"]:
         sources_valid &= digest(json.loads(support["value_json"]))==digest(result.evidence.normalized["values"][support["value_key"]])
         checked_values+=1
        if support["excerpt"]:
         _,parts=extract_document(result.resource)
         sources_valid &= any(support["excerpt"] in body for _,body in parts)
     checks={"real_model":bool(detail.get("model_history")) and all(x.get("response_id") and x.get("reported_model") for x in detail.get("model_history",[])),
       "actual_tools":any(not x.get("cached") and x["status"]=="ok" for x in detail["tool_history"]),
       "source_integrity":sources_valid,"structured_values":checked_values>0,
       "grounding_accepted":bool(packet) and packet["grounding_status"]!="validation_failed",
       "human_review":submitted.status_code==200 and submitted.json()["status"]=="pending_review",
       "clinical_state_preserved":before==after and unchanged}
     if mode=="multi":
      checks.update(specialists_called=all(a["execution_metadata"].get("response_id") for i,a in agents.items() if i!="A01" and a["state"]!="not_selected"),
       packet_complete=bool(packet and packet["packet_complete"]),no_failed_agents=all(a["state"]!="failed" for a in agents.values()),
       expected_abstention=(not packet["abstained"] if case=="complete" else packet["abstained"]),
       missing_prerequisite=(bool(packet["missing_information"]) if case=="missing_prerequisite" else True),
       conflicts=(bool(packet["conflicting_evidence"]) if case=="conflicting" else True))
     records[mode]={"checks":checks,"passed":all(checks.values()),"run":run}
    summary["cases"].append({"case":case,"source_snapshot":fingerprint,"same_source_snapshot":unchanged,**records})
    save()
    print(case, json.dumps({m:{"passed":records[m]["passed"],"checks":records[m]["checks"],"usage":records[m]["run"]["detail"]["usage"],"latency_ms":records[m]["run"]["detail"]["duration_ms"]} for m in records}),flush=True)
  finally:
   db.engine.dispose(); db.engine=original
summary["status"]="PASS" if all(c["multi"]["passed"] for c in summary["cases"]) else "FAIL"
save()
print("Report",report,"Status",summary["status"],flush=True)
sys.exit(0 if summary["status"]=="PASS" else 1)
