"""Read-only, authorized source text; no model and no inferred clinical facts."""
import base64,json
from pathlib import Path
from fastapi import APIRouter
from sqlalchemy import select
from app import db,service,history
from app.clinical.access import authorize,audit_access
from app.clinical.contracts import Event
from app.clinical.events import process
from app.clinical.gateway import ClinicalRetrieval,LocalFHIRProvider
from app.historical_candidates_schema import candidates
from app.record_facilities import assign
from app.rules import DEMO_TAG,SYSTEM
SOURCE="synthetic-source-documents"
SEED=Path(__file__).with_name("source_documents_seed_v1.json")

def seed(connection,actor,patient_id):
    scope=authorize(connection,actor,patient_id)
    patient=service.find(connection,db.patients,patient_id,required=True)["resource"]
    name=patient.get("name",[{}])[0];name=" ".join([*name.get("given",[]),name.get("family","")]).strip()
    prior=LocalFHIRProvider(connection).catalog(scope)
    for entry in json.loads(SEED.read_text()):
        identifier=patient_id+"-document-"+entry["id"]
        if any(row["resource_id"]==identifier for row in prior):continue
        body=entry["text"].format(name=name)
        resource={"resourceType":"DocumentReference","id":identifier,"meta":{"tag":[DEMO_TAG]},"subject":{"reference":"Patient/"+patient_id},
            "status":"current","docStatus":"final","date":entry["date"],"description":entry["title"],
            "type":{"coding":[{"system":SYSTEM,"code":entry["type"]}]},"author":[{"display":"Hospital B"}],
            "content":[{"attachment":{"contentType":"text/markdown","creation":entry["date"],"data":base64.b64encode(body.encode()).decode()}}]}
        result=process(connection,scope,Event(source=SOURCE,event_id=identifier+"-v1",event_time=entry["date"],resource=resource,version=1))
        assign(connection,actor,patient_id,result["evidence_id"],"Hospital B")

def list_documents(connection,actor,patient_id):
    scope=authorize(connection,actor,patient_id)
    rows=LocalFHIRProvider(connection).catalog(scope)
    cited=[dict(row) for row in connection.execute(select(candidates).where(candidates.c.patient_id==patient_id,candidates.c.archived.is_(False))).mappings()]
    answer=[]
    for row in rows:
        if row["kind"]!="DocumentReference":continue
        found=ClinicalRetrieval(connection,scope).get(evidence_id=row["id"])
        if found.resource is None:continue
        resource=found.resource;item=found.evidence.model_dump(mode="json")
        attachment=resource["content"][0]["attachment"]
        text=base64.b64decode(attachment["data"],validate=True).decode("utf-8")
        links=[]
        for candidate in cited:
            if any(pin["id"]==item["id"] for pin in candidate["source_refs"]):
                finding=candidate["rule_snapshot"]["equals"]
                links.append({"candidate_id":candidate["id"],"excerpt":finding if finding in text else None,"url":"/passport?candidate="+candidate["id"]+"&patient="+patient_id})
        facility=item["provenance"].get("facility",{}).get("origin") or next((a.get("display") for a in resource.get("author",[]) if a.get("display")),"Source facility unavailable")
        answer.append({"id":item["id"],"title":"Adolescent clinic note" if row["source"]==history.SOURCE else resource.get("description","Source document"),
            "facility":facility,"date":item["clinical_time"],"version":item["version"],"digest":item["digest"],"status":item["quality"]["state"],
            "simulated":facility=="Hospital A","text":text,"citations":links})
    audit_access(connection,scope,"source_documents_viewed")
    return answer

def router(Reader,write):
    routes=APIRouter(prefix="/api/v1/source-documents",tags=["Read-only source documents"])
    @routes.get("/patients/{patient_id}")
    def documents(patient_id:str,actor:Reader):return write(list_documents,actor,patient_id)
    return routes
