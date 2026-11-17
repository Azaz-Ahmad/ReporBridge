import os
from hmac import compare_digest
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db, service
from app.rules import DEMO_TAG, observation

app = FastAPI(title="Ajyra AI — ReproBridge", version="0.1.0",
              description="Synthetic illustration of care coordination across a life-stage transition.")
bearer = HTTPBearer(auto_error=False)


def identify(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    for role in ("coordinator", "reviewer", "viewer"):
        token = os.getenv(f"{role.upper()}_TOKEN")
        if credentials and token and compare_digest(credentials.credentials.encode(), token.encode()):
            return role
    raise HTTPException(401, "A valid demo access token is required", headers={"WWW-Authenticate": "Bearer"})


def require(expected):
    def authorize(role: Annotated[str, Depends(identify)]):
        if role != expected:
            raise HTTPException(403, f"Requires the demo {expected} role")
        return role
    return authorize


Coordinator = Annotated[str, Depends(require("coordinator"))]
Reviewer = Annotated[str, Depends(require("reviewer"))]
Reader = Annotated[str, Depends(identify)]


def write(operation, *args):
    with db.engine.begin() as connection:
        # Serialize the small demo's write transactions across local workers.
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(4280071)"))
        elif connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        return operation(connection, *args)


class ImportedResources(BaseModel):
    resources: list[dict] = Field(min_length=1, max_length=50)


class Review(BaseModel):
    decision: Literal["approve", "reject", "request_evidence"]
    note: str = Field(default="", max_length=300)
    evidence_refs: list[str] = Field(max_length=1000)


class Completion(BaseModel):
    scenario: Literal["verified", "conflicting"]


@app.get("/api/health")
def health():
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    except SQLAlchemyError as error:
        raise HTTPException(503, "Database or migrations unavailable") from error
    return {"status": "ready", "database": db.engine.dialect.name}


@app.get("/api/session")
def session(role: Reader):
    return {"role": role}


@app.get("/api/snapshot")
def snapshot(_: Reader):
    with db.engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        return service.snapshot(connection)


@app.post("/api/demo/seed")
def seed(actor: Coordinator):
    return {"patient_id": write(service.seed, actor)}


@app.post("/api/fhir/import")
def import_fhir(body: ImportedResources, actor: Coordinator):
    return {"patient_ids": write(service.import_records, actor, body.resources)}


@app.post("/api/patients/{patient_id}/evaluate")
def evaluate(patient_id: str, actor: Coordinator):
    return write(service.evaluate, actor, patient_id)


@app.post("/api/patients/{patient_id}/pregnancy")
def pregnancy(patient_id: str, actor: Coordinator):
    write(service.register_pregnancy, actor, patient_id)
    return {"stage": "pregnancy"}


@app.post("/api/obligations/{obligation_id}/agent")
def agent(obligation_id: str, actor: Coordinator):
    return write(service.execute_agent, actor, obligation_id)


@app.post("/api/tasks/{task_id}/review")
def review(task_id: str, body: Review, actor: Reviewer):
    return write(service.review, actor, task_id, body.decision, body.note, body.evidence_refs)


def record_completion(connection, actor, obligation_id, scenario):
    obligation = service.find(connection, db.obligations, obligation_id, required=True)
    if obligation["status"] == "closed":
        raise HTTPException(409, "The obligation is already closed")
    rule = service.find(connection, db.rules, obligation["rule_key"])["definition"]
    identifier = f"demo-{obligation_id}-{scenario}"
    resource = observation(obligation["patient_id"], identifier, rule["closure"],
                           "verified" if scenario == "verified" else "unresolved")
    service.import_records(connection, actor, [resource])
    return resource


@app.post("/api/obligations/{obligation_id}/demo-completion")
def completion(obligation_id: str, body: Completion, actor: Coordinator):
    return write(record_completion, actor, obligation_id, body.scenario)


@app.post("/api/obligations/{obligation_id}/close", responses={409: {"description": "Evidence or approval gate blocked closure"}})
def close(obligation_id: str, actor: Coordinator):
    result = write(service.close, actor, obligation_id)
    return JSONResponse(result, status_code=409 if result["status"] == "blocked" else 200)


@app.get("/api/fhir/patients/{patient_id}")
def export_fhir(patient_id: str, _: Reader):
    with db.engine.connect() as connection:
        patient = service.find(connection, db.patients, patient_id, required=True)
        resources = [patient["resource"], *service.evidence_for(connection, patient_id)]
        for obligation in service.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id):
            source = service.find(connection, db.evidence, obligation["source_id"])["resource"]
            rule = service.find(connection, db.rules, obligation["rule_key"])["definition"]
            identifier = obligation["id"]
            task = {
                "resourceType": "Task", "id": identifier, "meta": {"tag": [DEMO_TAG]},
                "status": "completed" if obligation["status"] == "closed" else "requested",
                "intent": "proposal", "for": {"reference": f"Patient/{patient_id}"},
                "owner": {"display": obligation["owner"]}, "authoredOn": obligation["created"],
                "description": rule["description"], "focus": {"reference": service.ref(source)},
                "identifier": [{"system": "https://reprobridge.example/obligations", "value": identifier}],
                "input": [{"type": {"text": "Illustrative rule version"}, "valueString": obligation["rule_key"]}],
            }
            for action in service.rows(connection, db.audit, db.audit.c.obligation_id == identifier):
                if action["action"] == "closure_verified":
                    task["output"] = [{"type": {"text": "Verified completion evidence"},
                                       "valueReference": {"reference": reference}} for reference in action["evidence_refs"]]
                resources.append({
                    "resourceType": "Provenance", "id": f"demo-audit-{action['sequence']}", "meta": {"tag": [DEMO_TAG]},
                    "target": [{"reference": f"Task/{identifier}"}], "recorded": action["recorded"],
                    "activity": {"text": action["action"]}, "agent": [{"who": {"display": action["actor"]}}],
                    "entity": [{"role": "source", "what": {"reference": reference}} for reference in action["evidence_refs"]],
                })
            resources.append(task)
        for resource in resources:
            if resource.get("entity") == []:
                del resource["entity"]
        return {"resourceType": "Bundle", "type": "collection", "entry": [
            {"fullUrl": f"https://reprobridge.example/fhir/{service.ref(resource)}", "resource": resource}
            for resource in resources
        ]}
