"""Actual transport bodies only. Reuse the existing mandatory secret scrubber."""
import hashlib,json,re,time
from uuid import uuid4
from fastapi import APIRouter
from sqlalchemy import select
from app import db,service
from app.clinical.access import authorize,audit_access,fail,now
from app.model_payload_schema import calls
MAX_BODY_BYTES=65536

def changed_paths(original,safe,path=""):
    if isinstance(original,dict) and isinstance(safe,dict):
        return [p for key,value in original.items() for p in ([path+"/"+key] if key not in safe else changed_paths(value,safe[key],path+"/"+key))]
    if isinstance(original,list) and isinstance(safe,list):return [p for i,(a,b) in enumerate(zip(original,safe)) for p in changed_paths(a,b,path+"/"+str(i))]
    return [] if original==safe else [path or "/"]

def safe_body(value):
    from app.investigation.replay import scrub
    safe=scrub(value);removed=changed_paths(value,safe)
    raw=json.dumps(safe,ensure_ascii=False,separators=(",",":"));encoded=raw.encode("utf-8")
    truncated=len(encoded)>MAX_BODY_BYTES
    body={"truncated_preview":encoded[:MAX_BODY_BYTES].decode("utf-8",errors="ignore")} if truncated else safe
    return body,removed,truncated,hashlib.sha256(encoded).hexdigest()

def manifest(value,patient):
    fields=[];records=[]
    def walk(v,path=""):
        if len(fields)>2000:return
        if isinstance(v,str):
            try:decoded=json.loads(v)
            except (ValueError,TypeError):return
            if isinstance(decoded,(dict,list)):walk(decoded,path+"/json")
        elif isinstance(v,dict):
            if isinstance(v.get("resourceType"),str) and isinstance(v.get("id"),str):records.append({"record":v["resourceType"]+"/"+str(v["id"]),"fields":list(v)})
            elif all(isinstance(v.get(key),str) for key in ("kind","resource_id","id")):records.append({"record":v["kind"]+"/"+v["resource_id"],"evidence_id":v["id"],"version":v.get("version"),"fields":list(v)})
            elif isinstance(v.get("reference"),str) and isinstance(v.get("excerpt"),str):records.append({"record":v["reference"],"fields":list(v)})
            for k,x in v.items():fields.append(path+"/"+k);walk(x,path+"/"+k)
        elif isinstance(v,list):
            for i,x in enumerate(v):walk(x,path+"/"+str(i))
    walk(value);raw=json.dumps(value,ensure_ascii=False).lower()
    names=[n for item in patient.get("name",[]) for n in [*item.get("given",[]),item.get("family","")] if len(n)>=3]
    return {"fields":fields[:2000],"records":records[:100],"manifest_truncated":len(fields)>2000 or len(records)>100,
        "patient_name_or_identifier_text_present":any(n.lower() in raw for n in names),
        "date_of_birth_present":bool(patient.get("birthDate") and patient["birthDate"] in raw),
        "name_detection_note":"Literal patient-name match; it may occur inside an identifier. Inspect the actual payload below."}

def persist(connection,scope,detail):
    context=authorize(connection,scope["actor"],scope["patient_id"])
    patient=service.find(connection,db.patients,scope["patient_id"],required=True)["resource"]
    # Headers/clients are never passed here. Existing scrub semantics are unchanged.
    request,rr,rt,rh=safe_body(detail.get("request_payload"));response,sr,st,sh=safe_body(detail.get("raw_response"))
    applied=detail.get("redactions",[])+rr+sr
    from app.investigation.replay import scrub
    manifest_value=manifest(scrub(detail.get("request_payload")),patient) if detail.get("original_capture_available") else {"available":False,"message":"Original request not recorded; fields and redactions are unknown."}
    if len(json.dumps(manifest_value).encode())>MAX_BODY_BYTES:manifest_value={"manifest_truncated":True,"preview":json.dumps(manifest_value)[:MAX_BODY_BYTES]}
    value={**detail,"request_payload":request,"raw_response":response,"redactions":applied,
        "redaction_label":("None applied" if not applied else "Existing mandatory secret scrub applied") if detail.get("original_capture_available") else "Unknown: original payload not recorded",
        "request_truncated":rt or detail.get("request_truncated",False),"response_truncated":st or detail.get("response_truncated",False),"request_stored_sha256":rh,"response_stored_sha256":sh,
        "context_manifest":manifest_value,"context_manifest_version":2}
    # Fail closed on key-like strings that the existing scrubber did not remove.
    serialized=json.dumps(value)
    if re.search(r"(?i)(?:sk-[a-z0-9_-]{8,}|Bearer\s+\S+)",serialized):
        fail(422,"unsafe_payload_storage","Provider payload was not stored because it contains credential-like material.")
    identifier="payload-"+uuid4().hex
    connection.execute(calls.insert().values(id=identifier,run_id=scope["run_id"],patient_id=scope["patient_id"],actor=scope["actor"],created=now(),detail=value))
    audit_access(connection,context,"model_payload_recorded")
    return {"id":identifier,**value}

def save(scope,detail):
    if not scope:return None
    from app.main import write
    return write(persist,scope,detail)

class Capture:
    def __init__(self,settings):self.settings=settings;self.pending={};self.records=[]
    def request(self,request):
        try:body=json.loads(request.content)
        except (ValueError,UnicodeError):body=request.content.decode("utf-8",errors="replace")
        self.pending[id(request)]=(time.perf_counter(),body)
    def failed(self,code):
        # No provider response exists. Preserve the actual prepared body, never invent usage.
        pending,self.pending=self.pending,{}
        for started,request in pending.values():
            stored=save(self.settings._payload_scope,{"mode":"live","replayed":False,"original_capture_available":True,"requested_model":self.settings.model,"reported_model":None,"provider_request_id":None,"http_status":None,"latency_ms":round((time.perf_counter()-started)*1000),"usage":None,"request_payload":request,"raw_response":None,"error":code,"capture_note":"Request prepared for transport; no provider response received. Remote delivery and usage are unknown."})
            if stored:self.records.append(stored)
    def response(self,response):
        started,request=self.pending.get(id(response.request),(time.perf_counter(),None))
        response.read()
        self.pending.pop(id(response.request),None)
        try:body=response.json()
        except ValueError:body=response.text
        detail={"mode":"live","replayed":False,"original_capture_available":True,"requested_model":self.settings.model,
            "reported_model":body.get("model") if isinstance(body,dict) else None,
            "provider_request_id":body.get("id") if isinstance(body,dict) else None,"http_status":response.status_code,
            "latency_ms":round((time.perf_counter()-started)*1000),"usage":body.get("usage") if isinstance(body,dict) else None,
            "request_payload":request,"raw_response":body}
        stored=save(self.settings._payload_scope,detail)
        if stored:self.records.append(stored)

def replay(settings,records):
    # Never reconstruct a wire call from fields or from today's re-bound context.
    if not records:records=[{"original_capture_available":False,"request_payload":None,"raw_response":None,"reported_model":None,"provider_request_id":None,"usage":None,"latency_ms":None}]
    for record in records:
        save(settings._payload_scope,{**record,"mode":"replay","replayed":True,"requested_model":settings.model,
            "original_call_id":record.get("id"),"capture_note":"Original recorded call, replayed; no provider request was sent." if record.get("original_capture_available") else "Legacy recording has no original wire payload. No payload has been reconstructed."})

def list_calls(connection,actor,patient_id):
    if actor not in {"coordinator","reviewer"}:fail(403,"payload_role_required","Model payload inspection requires Coordinator or Reviewer.")
    scope=authorize(connection,actor,patient_id);audit_access(connection,scope,"model_payload_index_viewed")
    return [{"id":row["id"],"run_id":row["run_id"],"created":row["created"],**{k:row["detail"].get(k) for k in ["requested_model","reported_model","mode","replayed","provider_request_id","usage","latency_ms","original_capture_available"]}}
        for row in connection.execute(select(calls).where(calls.c.patient_id==patient_id).order_by(calls.c.created.desc()).limit(100)).mappings()]

def view(connection,actor,identifier):
    if actor not in {"coordinator","reviewer"}:fail(403,"payload_role_required","Model payload inspection requires Coordinator or Reviewer.")
    row=connection.execute(select(calls).where(calls.c.id==identifier)).mappings().first()
    if not row:fail(404,"payload_unavailable","Model payload unavailable.")
    scope=authorize(connection,actor,row["patient_id"]);audit_access(connection,scope,"model_payload_viewed")
    service.audit(connection,actor,"model_payload_viewed",row["patient_id"],payload_id=identifier)
    return dict(row)

def router(Reader,write):
    routes=APIRouter(prefix="/api/v1/model-payloads",tags=["Audited model transport inspection"])
    @routes.get("/patients/{patient_id}")
    def index(patient_id:str,actor:Reader):return write(list_calls,actor,patient_id)
    @routes.get("/{identifier}")
    def detail(identifier:str,actor:Reader):return write(view,actor,identifier)
    return routes
