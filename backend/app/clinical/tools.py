"""Typed, scope-bound interfaces for future LangGraph tools."""
from pydantic import BaseModel, Field

from app import db
from app.clinical.access import audit_access, authorize
from app.clinical.contracts import Contract, EvidencePage, EvidenceResult, Filters, Identifier, Search
from app.clinical.gateway import ClinicalRetrieval, paginate
from app.service import rows


class EvidenceId(Contract):
    evidence_id: Identifier


class RelatedRequest(Contract):
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=1000)
    evidence_id: Identifier | None = None


class RelatedObligation(BaseModel):
    id: str
    rule_key: str
    owner: str
    status: str
    source_id: str


class RelatedPage(BaseModel):
    items: list[RelatedObligation]
    next_offset: int | None
    outcome: str


class ClinicalTools:
    def __init__(self, connection, trusted_context, policy=None):
        self.connection = connection
        self.context = authorize(connection, trusted_context.role, trusted_context.patient_id)
        self.retrieval = ClinicalRetrieval(connection, self.context, policy=policy)

    def get_patient_clinical_context(self, filters: Filters) -> EvidencePage:
        return self.retrieval.list(filters)

    def search_patient_observations(self, request: Search) -> EvidencePage:
        return self.retrieval.search(request.model_copy(update={"kind": "Observation", "mode": "structured"}))

    def search_patient_encounters(self, request: Search) -> EvidencePage:
        return self.retrieval.search(request.model_copy(update={"kind": "Encounter", "mode": "structured"}))

    def search_patient_documents(self, request: Search) -> EvidencePage:
        return self.retrieval.search(request.model_copy(update={"kind": "DocumentReference", "mode": "document"}))

    def get_evidence_provenance(self, request: EvidenceId) -> EvidenceResult:
        return self.retrieval.get(evidence_id=request.evidence_id).evidence

    def check_evidence_quality(self, request: EvidenceId) -> EvidenceResult:
        return self.retrieval.get(evidence_id=request.evidence_id).evidence

    def get_related_obligations(self, request: RelatedRequest) -> RelatedPage:
        patient_id = self.context.patient_id
        related = rows(self.connection, db.obligations, db.obligations.c.patient_id == patient_id)
        if request.evidence_id:
            evidence = self.retrieval.get(evidence_id=request.evidence_id).evidence
            related = [item for item in related if item["id"] in evidence.related_obligation_ids]
        page = paginate(sorted(related, key=lambda row: row["id"]), request)
        audit_access(self.connection, self.context, "related_obligations", page["outcome"])
        return RelatedPage(**{**page, "items": [RelatedObligation.model_validate(item) for item in page["items"]]})
