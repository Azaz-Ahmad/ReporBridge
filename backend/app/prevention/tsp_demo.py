"""Explicit synthetic fixture operations; preserve all existing closure/reviewer gates."""
from datetime import date, timedelta
from sqlalchemy import select
from app import db, demo, service as clinical
from app.clinical.access import authorize, fail, now
from app.clinical.contracts import Event
from app.clinical.events import process
from app.clinical.gateway import LocalFHIRProvider
from app.clinical.normalize import digest
from app.prevention import tsp
from app.rules import PRE, SYSTEM, observation, seed_records

SOURCE = "synthetic-tsp"
UNCERTAIN = "demo-tsp-uncertain"


def enabled():
    if not tsp.demo_enabled():
        fail(403, "demo_disabled", "TSP fixtures require DEMO_MODE.")


def dating_resources(patient_id, anchor, uncertain=False):
    origin = anchor - timedelta(days=95)
    registered = anchor - timedelta(days=14)
    result = []
    for suffix, code, value in [("lmp", "tsp-lmp", origin.isoformat()),
        ("us", "tsp-ultrasound-edd", (origin+timedelta(days=280+(12 if uncertain else 0))).isoformat()),
        ("registration", "pregnancy-registration", "registered")]:
        resource = observation(patient_id, patient_id+"-tsp-"+suffix, code, value)
        resource["effectiveDateTime"] = registered.isoformat()
        if suffix != "registration":
            resource.pop("valueString")
            resource["valueDateTime"] = value
        result.append(resource)
    return result


def load(connection, actor, session_id, reset=False):
    enabled()
    if reset:
        tsp.clock(connection, session_id, reset=True)
        if clinical.find(connection, db.patients, "demo-amira"):
            demo.reset_amira(connection, actor)
    anchor = date.fromisoformat(tsp.clock(connection, session_id)["as_of"])
    # Repeated seed does not move pregnancy dating when only the demo clock advances.
    old = clinical.rows(connection, db.audit, db.audit.c.patient_id == "demo-amira",
                        db.audit.c.action == "tsp_fixture_seeded")
    if old and not reset:
        anchor = date.fromisoformat(old[-1]["detail"]["anchor"])
    clinical.seed(connection, actor)
    patient = {**seed_records()[0], "id": UNCERTAIN,
               "name": [{"given": ["Uncertain"], "family": "Dating Demo"}]}
    existing = clinical.find(connection, db.patients, UNCERTAIN)
    if existing and existing["resource"] != patient:
        fail(409, "fixture_mismatch", "The uncertain-dating fixture identifier is already in use.")
    clinical.import_records(connection, actor, [patient, observation(UNCERTAIN, UNCERTAIN+"-flag", "follow-up-flag", "outstanding")])
    for patient_id in ("demo-amira", UNCERTAIN):
        clinical.evaluate(connection, actor, patient_id)
        clinical.register_pregnancy(connection, actor, patient_id)
        context = authorize(connection, actor, patient_id)
        for resource in dating_resources(patient_id, anchor, patient_id == UNCERTAIN):
            chain = [row for row in LocalFHIRProvider(connection).catalog(context)
                     if row["resource_id"] == resource["id"]]
            if any(row["source"] != SOURCE for row in chain):
                fail(409, "fixture_mismatch", "Dating fixture is owned by another source.")
            prior = max(chain, key=lambda row: row["version"], default=None)
            if prior and prior["resource"] == resource and prior["status"] == "final":
                continue
            version = prior["version"]+1 if prior else 1
            process(connection, context, Event(source=SOURCE, event_id=resource["id"]+"-v"+str(version),
                event_time=now(), resource=resource, version=version, action="put"))
    if not old or reset:
        clinical.audit(connection, actor, "tsp_fixture_seeded", "demo-amira", anchor=anchor.isoformat())
    return {"status": "ready", "anchor": anchor.isoformat(), "clock": tsp.clock(connection, session_id),
            "patients": ["demo-amira", UNCERTAIN], "synthetic_only": True}


def completion(connection, actor, obligation_id, session_id):
    enabled()
    obligation = clinical.find(connection, db.obligations, obligation_id, required=True)
    authorize(connection, actor, obligation["patient_id"])
    if obligation["patient_id"] != "demo-amira" or obligation["rule_key"] != PRE or obligation["status"] != "open":
        fail(409, "fixture_mismatch", "Completion fixture applies only to Amira's open carried obligation.")
    seeded = clinical.rows(connection, db.audit, db.audit.c.patient_id == "demo-amira", db.audit.c.action == "tsp_fixture_seeded")
    if not seeded:
        fail(409, "fixture_missing", "Load the TSP fixture first.")
    anchor = date.fromisoformat(seeded[-1]["detail"]["anchor"])
    # Explicit historical synthetic result, seven days before the seed anchor. No glucose value.
    completed = anchor - timedelta(days=7)
    if completed > date.fromisoformat(tsp.clock(connection, session_id)["as_of"]):
        fail(409, "future_evidence", "Advance the demo date to the synthetic result date before adding it.")
    resource = observation("demo-amira", "demo-"+obligation_id+"-verified", "follow-up-reconciled", "verified")
    resource["effectiveDateTime"] = completed.isoformat()
    clinical.import_records(connection, actor, [resource])
    if not clinical.rows(connection, db.audit, db.audit.c.obligation_id == obligation_id, db.audit.c.action == "tsp_completion_fixture"):
        clinical.audit(connection, actor, "tsp_completion_fixture", "demo-amira", obligation,
                       [clinical.ref(resource)], resource=resource, digest=digest(resource))
    return {"resource": resource, "note": "Synthetic result presence only; approval and verified closure remain separate."}


def allowed_completion(connection, resource):
    entries = clinical.rows(connection, db.audit, db.audit.c.patient_id == "demo-amira", db.audit.c.action == "tsp_completion_fixture")
    return any(entry["detail"].get("resource") == resource and entry["detail"].get("digest") == digest(resource) for entry in entries)


def invalidate(connection, actor, obligation_id):
    enabled()
    obligation = clinical.find(connection, db.obligations, obligation_id, required=True)
    context = authorize(connection, actor, obligation["patient_id"])
    candidates = clinical.closure_candidates(connection, obligation)
    if len(candidates) != 1 or not allowed_completion(connection, candidates[0]):
        fail(409, "fixture_mismatch", "Only the recorded TSP completion fixture may be invalidated here.")
    resource = candidates[0]
    chain = [row for row in LocalFHIRProvider(connection).catalog(context) if row["resource_id"] == resource["id"]]
    prior = max(chain,key=lambda row:row["version"])
    if prior["status"] == "invalidated":
        return {"status":"already_invalidated"}
    return process(connection, context, Event(source="workflow",event_id="tsp-invalidate-"+obligation_id,
        event_time=now(),resource=resource,version=prior["version"]+1,action="invalidate"))
