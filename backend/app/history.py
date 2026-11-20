"""SIMULATED earlier records and exact policy-data matching; never model judgement."""
import base64
import json
from pathlib import Path
from datetime import date, timedelta
from sqlalchemy import select
from app import db, service as clinical
from app.clinical.access import authorize, fail, now
from app.clinical.contracts import Event, Filters
from app.clinical.events import process
from app.clinical.gateway import ClinicalRetrieval, LocalFHIRProvider
from app.clinical.normalize import digest
from app.record_facilities import assign
from app.prevention import tsp
from app.rules import DEMO_TAG, SYSTEM

SEED_FILE=Path(__file__).with_name("history_seed_v1.json")
POLICY_FILE=Path(__file__).with_name("history_policy_v1.json")
SOURCE="synthetic-history-hospital-a"


def data():return json.loads(SEED_FILE.read_text(encoding="utf-8"))
def policy():return json.loads(POLICY_FILE.read_text(encoding="utf-8"))
def age(birth,day):return day.year-birth.year-((day.month,day.day)<(birth.month,birth.day))


def records(config):
    subject={"reference":"Patient/"+config["patient_id"]}
    provider={"type":"Organization","display":config["origin_facility"]}
    finding={"resourceType":"Observation","id":config["record_id"],"meta":{"tag":[DEMO_TAG]},
        "subject":subject,"status":"final","code":{"text":config["code_text"]},
        "effectiveDateTime":config["record_date"],"valueString":config["finding"],"performer":[provider]}
    body=("# SIMULATED provider exchange\n"+config["origin_facility"]+" recorded: "+config["finding"]+
          ". No follow-up closure is documented in this source. This is a historical source statement, not a current diagnosis or risk assessment.")
    document={"resourceType":"DocumentReference","id":config["document_id"],"meta":{"tag":[DEMO_TAG]},
        "subject":subject,"status":"current","docStatus":"final","date":config["record_date"],
        "type":{"coding":[{"system":SYSTEM,"code":"clinical-note"}]},"author":[provider],
        "context":{"period":{"start":config["record_date"]}},"description":"SIMULATED historical source document",
        "content":[{"attachment":{"contentType":"text/markdown","creation":config["record_date"],
            "data":base64.b64encode(body.encode()).decode()}}]}
    return finding,document


def seed(connection,actor):
    if not tsp.demo_enabled():fail(403,"demo_disabled","Simulated provider exchange requires DEMO_MODE.")
    config=data();clinical.seed(connection,actor)
    if config["patient_id"]!="demo-amira":fail(409,"fixture_identity","Preserve the existing synthetic identity.")
    clinical.register_pregnancy(connection,actor,config["patient_id"])
    scope=authorize(connection,actor,config["patient_id"])
    existing=LocalFHIRProvider(connection).catalog(scope)
    origin=date.fromisoformat(config["pregnancy_origin"])
    for suffix,code,value in [("lmp","tsp-lmp",origin.isoformat()),("us","tsp-ultrasound-edd",(origin+timedelta(days=280)).isoformat()),("registration","pregnancy-registration","registered")]:
        identifier="demo-amira-tsp-"+suffix
        if any(row["resource_id"]==identifier for row in existing):continue
        resource={"resourceType":"Observation","id":identifier,"meta":{"tag":[DEMO_TAG]},"subject":{"reference":"Patient/demo-amira"},
            "status":"final","code":{"coding":[{"system":SYSTEM,"code":code}]},"effectiveDateTime":config["registration_date"]}
        resource["valueString" if suffix=="registration" else "valueDateTime"]=value
        process(connection,scope,Event(source="synthetic-history-dating",event_id=identifier+"-v1",event_time=config["registration_date"]+"T08:00:00+00:00",resource=resource,version=1))
    return view(connection,actor,config["patient_id"])


def receive(connection,actor,patient_id):
    if not tsp.demo_enabled():fail(403,"demo_disabled","Simulated provider exchange requires DEMO_MODE.")
    authorize(connection,actor,patient_id)
    config=data()
    if patient_id!=config["patient_id"]:fail(404,"fixture_unavailable","This simulated source is not for this patient.")
    patient=clinical.find(connection,db.patients,patient_id,required=True)
    if patient["stage"]!="pregnancy":fail(409,"pregnancy_required","Register pregnancy before receiving earlier records.")
    scope=authorize(connection,actor,patient_id)
    for resource in records(config):
        chain=[row for row in LocalFHIRProvider(connection).catalog(scope) if row["resource_id"]==resource["id"]]
        if any(row["source"]!=SOURCE for row in chain):fail(409,"source_conflict","Preserve the original source authority.")
        prior=max(chain,key=lambda row:row["version"],default=None)
        if prior and prior["resource"]==resource:
            continue  # Never revive invalidated evidence or create a duplicate receipt.
        version=prior["version"]+1 if prior else 1
        result=process(connection,scope,Event(source=SOURCE,event_id=resource["id"]+"-v"+str(version),
            event_time=now(),resource=resource,version=version))
        assign(connection,actor,patient_id,result["evidence_id"],config["origin_facility"],config["receiving_facility"])
    return view(connection,actor,patient_id)


def view(connection,actor,patient_id,session_id=None):
    scope=authorize(connection,actor,patient_id);config=data();definition=policy()
    retrieval=ClinicalRetrieval(connection,scope)
    rows,*context=retrieval.prepare(Filters())
    evidence=[{**retrieval.result(row,*context).model_dump(mode="json"),"resource":row["resource"]} for row in rows if row["id"] not in context[0]]
    sources=[item for item in evidence if item["source"]==SOURCE and item["quality"]["state"]=="valid"]
    windows=tsp.patient_window(connection,actor,patient_id,session_id)
    obligations=clinical.rows(connection,db.obligations,db.obligations.c.patient_id==patient_id)
    traces=[]
    stage=clinical.find(connection,db.patients,patient_id,required=True)["stage"]
    for rule in definition["rules"]:
        matches=[item for item in sources if item["source"]==rule["source"] and item["kind"]==rule["resource_type"]
            and item["resource"].get("status")==rule["status"] and item["resource"].get("code",{}).get("text")==rule["code_text"]
            and item["normalized"]["values"].get(rule["value_key"])==rule["equals"]]
        open_work=[item for item in obligations if item["rule_key"]==rule["requires_open_rule"] and item["status"]=="open"]
        target=next((w for w in windows["windows"] if w["id"]==rule["target_window"]),None)
        triggered=bool(matches and open_work and stage==rule["requires_stage"] and target
            and windows["policy_id"]==definition["parent_policy_id"] and windows["policy_version"]==definition["parent_policy_version"])
        traces.append({"rule_id":rule["id"],"policy_id":definition["id"],"policy_version":definition["version"],
            "policy_hash":digest(definition),"triggered":triggered,"target_window":rule["target_window"],
            "evidence_ids":[item["id"] for item in matches],"obligation_ids":[item["id"] for item in open_work],
            "window":target if triggered else None,"citation":definition["citation"],
            "clinical_confirmation":definition["clinical_confirmation"],
            "reason":"Exact documented source + open obligation + pregnancy + existing window" if triggered else "Rule prerequisites not met"})
    selected=[{key:item[key] for key in ("id","kind","resource_id","version","digest","clinical_time","citation","provenance","quality")}|
        {"finding":item["resource"].get("valueString"),"source_url":"/api/v1/clinical/patients/"+patient_id+"/resources/"+item["kind"]+"/"+item["resource_id"]+"?version="+str(item["version"])} for item in sources]
    birth=date.fromisoformat(clinical.find(connection,db.patients,patient_id,required=True)["resource"]["birthDate"])
    return {"simulation":True,"label":"Simulated provider exchange — no live connection","patient_id":patient_id,
        "findings":selected,"rule_traces":traces,"window":windows,
        "age_at_record":age(birth,date.fromisoformat(config["record_date"][:10])),
        "age_at_registration":age(birth,date.fromisoformat(config["registration_date"])),
        "clinical_confirmation":definition["clinical_confirmation"]}
