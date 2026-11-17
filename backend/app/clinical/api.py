"""Register versioned clinical endpoints using existing authentication and transactions."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.clinical.access import PatientAccess, audit_access, authorize, claim, resolve
from app.clinical.contracts import (
    Event, EvidencePage, Filters, Identifier, Identity, PatientId, ResourcePage, ResourceResult, ResourceType,
    Search, SearchRequest,
)
from app.clinical.events import process
from app.clinical.fixtures import seed
from app.clinical.gateway import ClinicalRetrieval
from app.clinical.schema_v1 import changes
from app.clinical.tools import ClinicalTools


class IngestionResult(BaseModel):
    status: str
    evidence_id: str


class IdentityResult(BaseModel):
    status: str
    patient_id: str


class Change(BaseModel):
    sequence: int
    patient_id: str
    evidence_id: str
    action: str
    received: str
    related_obligations: list[str]


class FixtureResult(BaseModel):
    patient_id: str
    events: int
    duplicates: int


class ErrorDetail(BaseModel):
    code: str
    message: str


class ClinicalError(BaseModel):
    detail: ErrorDetail


def router(reader, coordinator, write):
    routes = APIRouter(prefix="/api/v1/clinical", tags=["clinical foundation"],
                       responses={code: {"model": ClinicalError} for code in (401, 403, 404, 409, 422)})
    patient = "/patients/{patient_id}"

    def run(connection, role, patient_id, operation):
        context = authorize(connection, role, patient_id)
        return operation(connection, context)

    def scoped(role, patient_id, operation):
        try:
            return write(run, role, patient_id, operation)
        except HTTPException as error:
            if error.status_code in (403, 404, 409):
                write(audit_access, PatientAccess(role, patient_id), "clinical_request_denied", str(error.status_code))
            raise

    @routes.get(patient + "/resources", response_model=ResourcePage)
    def resources(patient_id: PatientId, role: reader, filters: Annotated[Filters, Query()]):
        return scoped(role, patient_id, lambda db, ctx: ClinicalRetrieval(db, ctx).list(filters, raw=True))

    @routes.get(patient + "/resources/{kind}/{resource_id}", response_model=ResourceResult)
    def resource(patient_id: PatientId, kind: ResourceType, resource_id: Identifier, role: reader,
                 version: Annotated[int | None, Query(ge=1, le=2147483647)] = None):
        return scoped(role, patient_id, lambda db, ctx: ClinicalRetrieval(db, ctx).get(
            kind=kind, resource_id=resource_id, version=version))

    @routes.get(patient + "/evidence", response_model=EvidencePage)
    def evidence(patient_id: PatientId, role: reader, filters: Annotated[Filters, Query()]):
        return scoped(role, patient_id, lambda db, ctx: ClinicalRetrieval(db, ctx).list(filters))

    @routes.get(patient + "/evidence/{evidence_id}", response_model=ResourceResult)
    def evidence_by_id(patient_id: PatientId, evidence_id: Identifier, role: reader):
        return scoped(role, patient_id, lambda db, ctx: ClinicalRetrieval(db, ctx).get(evidence_id=evidence_id))

    @routes.get(patient + "/documents", response_model=EvidencePage)
    def documents(patient_id: PatientId, role: reader, filters: Annotated[Search, Query()]):
        return scoped(role, patient_id, lambda db, ctx: (
            ClinicalTools(db, ctx).search_patient_documents(filters) if filters.query else
            ClinicalRetrieval(db, ctx).list(filters.model_copy(update={"kind": "DocumentReference"}))))

    @routes.post("/retrieval/search", response_model=EvidencePage)
    def search(body: SearchRequest, role: reader):
        return scoped(role, body.patient_id, lambda db, ctx: ClinicalRetrieval(db, ctx).search(body))

    @routes.post(patient + "/events", response_model=IngestionResult)
    def ingest(patient_id: PatientId, body: Event, role: coordinator):
        return scoped(role, patient_id, lambda db, ctx: process(db, ctx, body))

    @routes.post(patient + "/identity/claims", response_model=IdentityResult)
    def identity_claim(patient_id: PatientId, body: Identity, role: coordinator):
        return scoped(role, patient_id, lambda db, ctx: {
            "status": claim(db, ctx, body.namespace, body.external_id), "patient_id": patient_id})

    @routes.post(patient + "/identity/resolve", response_model=IdentityResult)
    def identity_resolve(patient_id: PatientId, body: Identity, role: coordinator):
        def lookup(db, ctx):
            canonical = resolve(db, ctx, body.namespace, body.external_id)
            audit_access(db, ctx, "identity_resolved")
            return {"status": "mapped", "patient_id": canonical}
        return scoped(role, patient_id, lookup)

    @routes.get(patient + "/changes", response_model=list[Change])
    def notifications(patient_id: PatientId, role: reader, after: Annotated[int, Query(ge=0)] = 0,
                      limit: Annotated[int, Query(ge=1, le=50)] = 20):
        def feed(db, ctx):
            audit_access(db, ctx, "change_feed")
            return [dict(row) for row in db.execute(select(changes).where(
                changes.c.patient_id == ctx.patient_id, changes.c.sequence > after
            ).order_by(changes.c.sequence).limit(limit)).mappings()]
        return scoped(role, patient_id, feed)

    @routes.post("/demo/dataset", response_model=FixtureResult)
    def load_fixture(role: coordinator):
        return write(seed, role)

    return routes
