"""Default synthetic presentation cohort; no rules or historical records are changed."""
from datetime import date, timedelta
from app import db, service
from app.clinical.access import authorize, now
from app.clinical.contracts import Event
from app.clinical.events import process
from app.clinical.gateway import LocalFHIRProvider
from app.prevention.tsp import DEFAULT_AS_OF
from app.prevention.tsp_demo import dating_resources
from app.rules import observation, seed_records

COHORT = {"demo-amira": ("Amira", "Haddad", "Carry a preconception glycemic assessment into pregnancy"),
          "demo-lina": ("Lina", "Omar", "Review a prevention window that has passed"),
          "demo-sara": ("Sara", "Ali", "Prepare for an upcoming prevention window")}


def seed(connection, actor):
    service.seed(connection, actor)
    for identifier, (given, family, reason) in COHORT.items():
        if identifier != "demo-amira":
            patient = {**seed_records()[0], "id": identifier, "name": [{"given": [given], "family": family}]}
            service.import_records(connection, actor, [patient, observation(identifier, identifier+"-flag", "follow-up-flag", "outstanding")])
        service.evaluate(connection, actor, identifier)
        service.register_pregnancy(connection, actor, identifier)
        scope = authorize(connection, actor, identifier)
        existing = LocalFHIRProvider(connection).catalog(scope)
        # Pin first-seeded dates. Ordinary replay never corrects or revives evidence.
        if any(item["resource_id"] == identifier+"-tsp-lmp" for item in existing):
            continue
        anchor = DEFAULT_AS_OF + timedelta(days={"demo-amira": 0,"demo-lina": -110,"demo-sara": -67}[identifier])
        for resource in dating_resources(identifier, anchor):
            process(connection, scope, Event(source="synthetic-jury",event_id=resource["id"]+"-v1",event_time="2026-01-01T00:00:00+00:00",resource=resource,version=1))
        service.audit(connection,actor,"jury_demo_reason",identifier,reason=reason)
    from app.source_documents import seed as seed_documents
    for patient_id in COHORT:seed_documents(connection,actor,patient_id)
    return {"patient_id":"demo-amira","patient_ids":list(COHORT),"synthetic_only":True}
