from app.historical_candidates_api import router as historical_candidates_router
import os
from contextlib import nullcontext
from threading import RLock
from hmac import compare_digest
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db, demo, service
from app.fhir import check_references, structure_errors
from app.agent import NODES
from app.clinical.access import audit_access, authorize, permitted
from app.clinical.api import router as clinical_router
from app.investigation.api import router as investigation_router
from app.prevention.api import router as prevention_router
from app.prevention import service as prevention
from app.prevention.tsp_api import router as tsp_router
from app.handoff_api import router as handoff_router
from app.history_api import router as history_router
from app.rules import DEMO_TAG, observation

app = FastAPI(title="Ajyra AI - ReproBridge", version="0.6.0",
              description="Synthetic illustration of care coordination across a life-stage transition.")
bearer = HTTPBearer(auto_error=False)


def identify(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    roles = []
    for role in ("coordinator", "reviewer", "viewer"):
        token = os.getenv(f"{role.upper()}_TOKEN")
        if credentials and token and compare_digest(credentials.credentials.encode(), token.encode()):
            roles.append(role)
    if len(roles) == 1:
        return roles[0]
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


_sqlite_writer = RLock()


def write(operation, *args):
    # Queue local SQLite writers before opening a transaction. Keep database-level
    # serialization for other processes and the existing PostgreSQL advisory lock.
    with _sqlite_writer if db.engine.dialect.name == "sqlite" else nullcontext():
        with db.engine.begin() as connection:
            # Serialize the small demo's write transactions across local workers.
            if connection.dialect.name == "postgresql":
                connection.execute(text("SELECT pg_advisory_xact_lock(4280071)"))
            elif connection.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            result = operation(connection, *args)
            prevention.synchronize(connection)
            return result

app.include_router(clinical_router(Reader, Coordinator, write))
app.include_router(investigation_router(Reader, Coordinator, Reviewer, write))
app.include_router(prevention_router(Reader, Coordinator, Reviewer, write))
app.include_router(tsp_router(Reader, Coordinator, write))
app.include_router(handoff_router(Reader, Coordinator, write))
app.include_router(history_router(Reader, Coordinator, write))
app.include_router(historical_candidates_router(Reader, Reviewer, write))


@app.exception_handler(HTTPException)
async def clinical_http_error(request, error):
    if request.url.path.startswith("/api/v1/clinical/") and isinstance(error.detail, str):
        code = {401: "authentication_required", 403: "forbidden", 404: "not_found"}.get(
            error.status_code, "clinical_request_failed")
        return JSONResponse(status_code=error.status_code, headers=error.headers,
                            content={"detail": {"code": code, "message": error.detail}})
    return await http_exception_handler(request, error)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    if request.url.path.startswith(("/api/v1/clinical/", "/api/v1/agents/", "/api/v1/prevention/")):
        return JSONResponse(status_code=422, content={"detail": {
            "code": "invalid_request", "message": "Clinical request failed validation."}})
    return await request_validation_exception_handler(request, error)


def authorized_patient_action(connection, actor, patient_id, operation):
    authorize(connection, actor, patient_id)
    return operation(connection, actor, patient_id)


def authorized_obligation_action(connection, actor, obligation_id, operation, *args):
    obligation = service.find(connection, db.obligations, obligation_id, required=True)
    authorize(connection, actor, obligation["patient_id"])
    return operation(connection, actor, obligation_id, *args)


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
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if revision != "0010":
                raise HTTPException(503, "Run the clinical foundation database migration.")
    except SQLAlchemyError as error:
        raise HTTPException(503, "Database or migrations unavailable") from error
    return {"status": "ready", "database": db.engine.dialect.name}


@app.get("/api/session")
def session(role: Reader):
    return {"role": role, "demo_mode": os.getenv("DEMO_MODE", "").lower() in {"true", "1", "yes"}}


def read_snapshot(operation, *args):
    with db.engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        elif connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN")
        return operation(connection, *args)


@app.get("/api/snapshot")
def snapshot(role: Reader):
    return read_snapshot(workspace_snapshot, role)


def workspace_snapshot(connection, role):
    patients = permitted(connection, role)
    result = service.snapshot(connection, patients)
    result["case_context"] = {
        item["id"]: context for item in result["clinical_obligations"]
        if (context := service.clinical_presentation(connection, item))
    }
    result["workflow_nodes"] = [node.__name__ for node in NODES]
    result["closure_readiness"] = {
        item["id"]: service.assess_closure(connection, item)[0]
        for item in result["clinical_obligations"] if item["status"] == "open"
    }
    result["demo_run_archive"] = [item for item in demo.archive_summaries(connection)
                                  if item["patient_id"] in patients]
    return result


@app.post("/api/demo/seed")
def seed(actor: Coordinator):
    if os.getenv("REPROBRIDGE_TEST_MODE") == "true":
        return {"patient_id": write(service.seed, actor)}
    from app.jury import seed as jury_seed
    return write(jury_seed, actor)


@app.post("/api/demo/reset-amira")
def reset_amira(actor: Coordinator):
    def reset_granted_fixture(connection, actor):
        authorize(connection, actor, "demo-amira")
        return demo.reset_amira(connection, actor)
    return write(reset_granted_fixture, actor)


@app.post("/api/fhir/import")
def import_fhir(body: ImportedResources, actor: Coordinator):
    return {"patient_ids": write(service.import_records, actor, body.resources)}


@app.post("/api/patients/{patient_id}/evaluate")
def evaluate(patient_id: str, actor: Coordinator):
    return write(authorized_patient_action, actor, patient_id, service.evaluate)


@app.post("/api/patients/{patient_id}/pregnancy")
def pregnancy(patient_id: str, request: Request, actor: Coordinator):
    write(authorized_patient_action, actor, patient_id, lambda connection, role, identifier: service.register_pregnancy(connection, role, identifier, request.cookies.get("reprobridge-demo-session")))
    return {"stage": "pregnancy"}


@app.post("/api/obligations/{obligation_id}/agent")
def agent(obligation_id: str, actor: Coordinator):
    result = write(authorized_obligation_action, actor, obligation_id, service.execute_agent)
    return JSONResponse(result, status_code=503 if result["status"] == "failed" else 200)


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
    return write(authorized_obligation_action, actor, obligation_id, record_completion, body.scenario)


@app.post("/api/obligations/{obligation_id}/close", responses={409: {"description": "Evidence or approval gate blocked closure"}})
def close(obligation_id: str, actor: Coordinator):
    result = write(authorized_obligation_action, actor, obligation_id, service.close)
    return JSONResponse(result, status_code=409 if result["status"] == "blocked" else 200)


class FHIRResponse(JSONResponse):
    media_type = "application/fhir+json"


@app.get("/api/fhir/patients/{patient_id}", response_class=FHIRResponse)
def export_fhir(patient_id: str, role: Reader):
    def scoped_export(connection, actor, patient_id):
        context = authorize(connection, actor, patient_id)
        bundle = patient_bundle(connection, patient_id)
        audit_access(connection, context, "fhir_bundle")
        return bundle
    return write(scoped_export, role, patient_id)


def patient_bundle(connection, patient_id):
    from app.handoff_provenance import export_agents
    patient = service.find(connection, db.patients, patient_id, required=True)
    resources = [patient["resource"], *service.decision_evidence_for(connection, patient_id)]
    for obligation in service.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id):
        source = service.find(connection, db.evidence, obligation["source_id"])["resource"]
        rule = service.find(connection, db.rules, obligation["rule_key"])["definition"]
        identifier = obligation["id"]
        task = {
            "resourceType": "Task", "id": identifier, "meta": {"tag": [DEMO_TAG]},
            "status": "completed" if obligation["status"] == "closed" else "requested",
            "intent": "proposal", "for": {"reference": f"Patient/{patient_id}"},
            "owner": {"display": obligation["owner"]}, "authoredOn": obligation["created"],
            "description": service.clinical_presentation(connection, obligation).get("next_action", rule["description"]),
            "focus": {"reference": service.ref(source)},
            "identifier": [{"system": "https://reprobridge.example/obligations", "value": identifier}],
            "input": [{"type": {"text": "Illustrative rule version"}, "valueString": obligation["rule_key"]}],
        }
        actions = service.rows(connection, db.audit, db.audit.c.obligation_id == identifier)
        for action in sorted(actions, key=lambda entry: entry["sequence"]):
            if obligation["status"] == "closed" and action["action"] == "closure_verified":
                task["output"] = [{"type": {"text": "Verified completion evidence"},
                                   "valueReference": {"reference": reference}} for reference in action["evidence_refs"]]
            resources.append({
                "resourceType": "Provenance", "id": f"demo-audit-{action['sequence']}", "meta": {"tag": [DEMO_TAG]},
                "target": [{"reference": f"Task/{identifier}"}], "recorded": action["recorded"],
                "activity": {"text": ("SIMULATED — " if action["detail"].get("simulation") else "") + action["action"]},
                "agent": [{"who": {"display": action["actor"]}}, *export_agents(action)],
                "entity": [{"role": "source", "what": {"reference": reference}} for reference in action["evidence_refs"]],
            })
        resources.append(task)
    for resource in resources:
        if resource.get("entity") == []:
            del resource["entity"]
    if len(resources) > 250:
        raise HTTPException(413, "Bundle exceeds the demo export limit. Use paginated clinical retrieval.")
    check_references(resources)
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        {"fullUrl": f"https://reprobridge.example/fhir/{service.ref(resource)}", "resource": resource}
        for resource in resources
    ]}
    if structure_errors(bundle):
        raise HTTPException(409, "The stored patient record cannot be exported as this FHIR R4 bundle.")
    return bundle


@app.post("/api/demo/jury-seed")
def jury_seed(actor: Coordinator):
    from app.jury import seed
    from app.prevention.tsp import demo_enabled
    if not demo_enabled():
        raise HTTPException(403, "Demo mode is required.")
    return write(seed, actor)


@app.middleware("http")
async def diagnostic_fixture_mode(request, call_next):
    path = request.url.path
    diagnostic = path in {"/api/v1/clinical/demo/dataset", "/api/v1/prevention/demo/timing", "/api/v1/simulated-handoff/demo/seed"} or path.startswith("/api/v1/tsp/demo/")
    if request.method == "POST" and diagnostic and os.getenv("REPROBRIDGE_TEST_MODE") != "true":
        return JSONResponse(status_code=403,content={"detail":{"code":"test_mode_required", "message":"Diagnostic fixtures require test mode. Use the default three-patient demo seed."}})
    return await call_next(request)
