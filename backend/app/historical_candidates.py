"""Policy-data identification, explicit human review, existing evidence/closure machinery."""
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from app import db, service
from app.clinical.access import authorize, permitted, fail, now
from app.clinical.contracts import Event, Filters
from app.clinical.gateway import ClinicalRetrieval
from app.clinical.normalize import digest
from app.historical_candidates_schema import candidates
from app.prevention import tsp
from app.rules import observation

POLICY_FILE=Path(__file__).with_name("historical_relevance_policy_v1.json")
LABELS={"candidate":"Candidate: needs clinician confirmation","confirmed":"Confirmed by clinician","dismissed":"Dismissed by clinician","withdrawn":"Withdrawn: trigger evidence no longer valid"}
def policy():return json.loads(POLICY_FILE.read_text(encoding="utf-8"))
def entries(connection,patient_id):
    return [dict(row) for row in connection.execute(select(candidates).where(candidates.c.patient_id==patient_id,candidates.c.archived.is_(False))).mappings()]
def event(connection,actor,row,action,session_id=None,**detail):
    current=tsp.clock(connection,session_id)
    # Candidate events cite the M08 registry; keep them outside legacy Task provenance.
    # The normal obligation has its own unchanged workflow-resource audit trail.
    service.audit(connection,actor,action,row["patient_id"],None,
        [item["kind"]+"/"+item["resource_id"] for item in row["source_refs"]],
        candidate_id=row["id"],candidate_title=row["title"],linked_obligation_id=row.get("obligation_id"),relevance_rule_id=row["rule_id"],
        relevance_rule_version=row["rule_version"],demo_date=current["as_of"] if current["demo_mode"] else None,**detail)

def sources(connection,actor,patient_id):
    context=authorize(connection,actor,patient_id)
    retrieval=ClinicalRetrieval(connection,context)
    rows,*metadata=retrieval.prepare(Filters())
    return [{**retrieval.result(row,*metadata).model_dump(mode="json"),"resource":row["resource"]}
            for row in rows if row["id"] not in metadata[0]]

def matched(rule,items):
    return [item for item in items if item["source"]==rule["source"] and item["kind"]==rule["resource_type"]
        and item["quality"]["state"]=="valid" and item["resource"].get("status")==rule["status"]
        and item["resource"].get("code",{}).get("text")==rule["code_text"]
        and item["normalized"]["values"].get(rule["value_key"])==rule["equals"]]

def pins(rule,items,matches):
    selected=[*matches,*[item for item in items if item["source"]==rule["source"] and item["kind"] in rule.get("supporting_resource_types",[]) and item["quality"]["state"]=="valid"]]
    return [{**{key:item[key] for key in ("id","kind","resource_id","version","digest","clinical_time","provenance")},
        "trigger":item in matches,"source_url":"/api/v1/clinical/patients/"+item["patient_id"]+"/evidence/"+item["id"]}
        for item in sorted(selected,key=lambda value:(value["kind"],value["id"]))]

def evaluate(connection,actor,patient_id,session_id=None):
    authorize(connection,actor,patient_id)
    patient=service.find(connection,db.patients,patient_id,required=True)
    if patient["stage"]!="pregnancy":return []
    transition=connection.execute(select(db.events.c.id).where(db.events.c.patient_id==patient_id,db.events.c.stage=="pregnancy")).scalar_one_or_none()
    if not transition:return []
    rules=policy()["rules"]
    # Avoid retrieval/window work for the many unrelated M08 feeds in the demo.
    from app.clinical.gateway import LocalFHIRProvider
    catalog=LocalFHIRProvider(connection).catalog(authorize(connection,actor,patient_id))
    if not any(item["source"] in {rule["source"] for rule in rules} for item in catalog):return []
    items=sources(connection,actor,patient_id)
    prior=entries(connection,patient_id)
    for rule in rules:
        if patient["stage"]!=rule["requires_stage"]:continue
        existing=next((item for item in prior if item["transition_id"]==transition and item["rule_id"]==rule["id"] and item["rule_version"]==rule["version"]),None)
        matching=matched(rule,items)
        if existing and existing["status"] in {"dismissed","withdrawn"}:continue
        valid_trigger_ids={item["id"] for item in matching}
        pinned_trigger_changed=existing and any(pin["trigger"] and pin["id"] not in valid_trigger_ids for pin in existing["source_refs"])
        if existing and (not matching or pinned_trigger_changed):
            withdraw(connection,actor,existing,session_id)
            continue
        if not matching:continue
        references=pins(rule,items,matching)
        if existing:
            if existing["source_refs"]!=references and existing["status"]=="candidate":
                connection.execute(candidates.update().where(candidates.c.id==existing["id"]).values(source_refs=references,updated=now()))
                event(connection,actor,{**existing,"source_refs":references},"historical_candidate_sources_updated",session_id)
            continue
        stamp=now();clock=tsp.clock(connection,session_id)
        row=dict(id=uuid4().hex,patient_id=patient_id,transition_id=transition,rule_id=rule["id"],rule_version=rule["version"],
            title=rule["title"],owner_role=rule["owner_role"],status="candidate",created=stamp,demo_date=clock["as_of"],updated=stamp,
            rule_snapshot=rule,source_refs=references,window_snapshot=tsp.patient_window(connection,actor,patient_id,session_id),
            decision=None,obligation_id=None,confirmation_resource=None,archived=False)
        connection.execute(candidates.insert().values(**row))
        event(connection,actor,row,"historical_candidate_identified",session_id)
    return entries(connection,patient_id)

def observe_event(connection,actor,patient_id,source,session_id=None):
    if any(rule["source"]==source for rule in policy()["rules"]):evaluate(connection,actor,patient_id,session_id)

def withdraw(connection,actor,row,session_id=None):
    connection.execute(candidates.update().where(candidates.c.id==row["id"]).values(status="withdrawn",updated=now()))
    event(connection,actor,row,"historical_candidate_withdrawn",session_id,reason="The policy-matched trigger evidence is no longer valid.")
    if row.get("confirmation_resource"):
        from app.clinical.gateway import LocalFHIRProvider
        from app.clinical.events import process
        context=authorize(connection,actor,row["patient_id"])
        chain=[item for item in LocalFHIRProvider(connection).catalog(context) if item["resource_id"]==row["confirmation_resource"]["id"] and item["source"]=="workflow"]
        latest=max(chain,key=lambda item:item["version"])
        if latest["status"]!="invalidated":
            process(connection,context,Event(source="workflow",event_id="history-withdraw-"+row["id"]+"-v"+str(latest["version"]+1),
                event_time=now(),version=latest["version"]+1,action="invalidate",resource=latest["resource"]))

def current_row(connection,actor,identifier):
    row=connection.execute(select(candidates).where(candidates.c.id==identifier,candidates.c.archived.is_(False))).mappings().first()
    if not row:fail(404,"candidate_unavailable","Candidate is unavailable.")
    authorize(connection,actor,row["patient_id"])
    return dict(row)

def review(connection,actor,identifier,decision,rationale,session_id=None):
    if actor!="reviewer":fail(403,"reviewer_required","Candidate review requires the existing Reviewer role.")
    row=current_row(connection,actor,identifier)
    if row["status"]!="candidate":fail(409,"candidate_not_pending","Candidate is no longer awaiting confirmation.")
    if not rationale.strip():fail(422,"rationale_required","A clinician rationale is required.")
    # A review does not perform identification or trust model classifications. Recheck pinned facts.
    live_policy=next((rule for rule in policy()["rules"] if rule["id"]==row["rule_id"] and rule["version"]==row["rule_version"]),None)
    if not live_policy or digest(live_policy)!=digest(row["rule_snapshot"]):fail(409,"candidate_policy_changed","Policy changed; reconcile the candidate before reviewing.")
    items=sources(connection,actor,row["patient_id"])
    matches=matched(live_policy,items)
    if not matches or pins(live_policy,items,matches)!=row["source_refs"]:fail(409,"candidate_sources_changed","Trigger evidence changed; refresh the candidate before review.")
    stamp=now();normal=None;confirmation=None
    if decision=="confirm":
        definition=live_policy["lifecycle_rule"]
        key=definition["id"];configured=service.find(connection,db.rules,key)
        persisted={k:v for k,v in definition.items() if k!="id"}
        if configured and configured["definition"]!=persisted:fail(409,"immutable_rule","Persisted lifecycle rule differs from the policy version.")
        if not configured:
            if not service.find(connection,db.pathways,definition["pathway"]):
                connection.execute(db.pathways.insert().values(id=definition["pathway"],label=definition["pathway"]))
            rule_id,version=key.split("@")
            connection.execute(db.rules.insert().values(id=key,rule_id=rule_id,version=version,pathway_id=definition["pathway"],definition=persisted))
        if service.rows(connection,db.obligations,db.obligations.c.patient_id==row["patient_id"],db.obligations.c.rule_key==key):
            fail(409,"obligation_exists","An obligation for this lifecycle rule already exists.")
        confirmation=observation(row["patient_id"],"demo-"+row["id"]+"-confirmed",definition["trigger"],definition["value"])
        confirmation["effectiveDateTime"]=tsp.clock(connection,session_id)["as_of"]
        confirmation["code"]["text"]="Synthetic clinician confirmation of historical review candidate"
        service.import_records(connection,actor,[confirmation])
        normal=dict(id=uuid4().hex,patient_id=row["patient_id"],rule_key=key,source_id=confirmation["id"],owner=row["owner_role"],status="open",created=stamp)
        connection.execute(db.obligations.insert().values(**normal))
        service.audit(connection,actor,"obligation_created",row["patient_id"],normal,[service.ref(confirmation)],candidate_id=row["id"],origin="identified_from_earlier_records")
    state="confirmed" if decision=="confirm" else "dismissed"
    outcome={"decision":decision,"rationale":rationale.strip(),"actor":actor,"recorded":stamp,"demo_date":tsp.clock(connection,session_id)["as_of"]}
    connection.execute(candidates.update().where(candidates.c.id==identifier).values(status=state,decision=outcome,updated=stamp,
        obligation_id=normal["id"] if normal else None,confirmation_resource=confirmation))
    event(connection,actor,{**row,"obligation_id":normal["id"] if normal else None},"historical_candidate_"+state,session_id,rationale=rationale.strip())
    return public(connection,actor,current_row(connection,actor,identifier),session_id)

def public(connection,actor,row,session_id=None,window=None):
    window=window if window is not None else tsp.patient_window(connection,actor,row["patient_id"],session_id)
    target=next((item for item in window["windows"] if item["id"]==row["rule_snapshot"]["target_window"]),None)
    return {key:row[key] for key in ("id","patient_id","title","owner_role","status","created","demo_date","rule_id","rule_version","source_refs","decision","obligation_id")} | {
        "status_label":LABELS[row["status"]],"clinical_confirmation":"pending clinical confirmation",
        "eligibility_criteria":[text.format(**row["rule_snapshot"]) for text in row["rule_snapshot"]["eligibility_criteria"]],"target_window":row["rule_snapshot"]["target_window"],
        "window":target,"calculator_status":window["status"],"as_of":window["as_of"],
        "window_policy_id":window["policy_id"],"window_policy_version":window["policy_version"]}

def list_patient(connection,actor,patient_id,session_id=None):
    authorize(connection,actor,patient_id)
    found=entries(connection,patient_id)
    if not found:return []
    window=tsp.patient_window(connection,actor,patient_id,session_id)
    return [public(connection,actor,row,session_id,window) for row in found]

def queue(connection,actor):
    allowed=permitted(connection,actor)
    return [{key:row[key] for key in ("id","patient_id","title","owner_role","status","demo_date","obligation_id")}
        for row in connection.execute(select(candidates).where(candidates.c.patient_id.in_(allowed),candidates.c.archived.is_(False))).mappings()]

def reset_allowlist(connection,patient_id):
    return {row["obligation_id"]:row for row in entries(connection,patient_id) if row["obligation_id"]}

def archive_for_reset(connection,patient_id):
    rows=entries(connection,patient_id)
    connection.execute(candidates.update().where(candidates.c.patient_id==patient_id,candidates.c.archived.is_(False)).values(archived=True))
    return rows
