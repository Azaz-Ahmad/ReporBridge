"""Strict model drafts and backend-owned review packets."""
from typing import Literal
from pydantic import ConfigDict, Field
from app.clinical.contracts import Contract, PatientId, Identifier


class StrictContract(Contract):
    model_config = ConfigDict(extra="forbid", strict=True)


class RunRequest(StrictContract):
    patient_id: PatientId
    question: str = Field(min_length=12, max_length=800)
    request_id: Identifier
    synthetic_only: Literal[True]


class Support(StrictContract):
    evidence_id: str = Field(max_length=100)
    version: int = Field(ge=1)
    excerpt: str = Field(max_length=1000)
    value_key: str = Field(max_length=80)
    value_json: str = Field(max_length=2000)


class Finding(StrictContract):
    finding_id: str = Field(max_length=80)
    statement: str = Field(min_length=1, max_length=1000)
    supporting_sources: list[Support] = Field(max_length=8)
    evidence_status: Literal["available", "missing", "conflicting", "historical"]
    requires_clinical_interpretation: bool


class Draft(StrictContract):
    summary: str = Field(min_length=1, max_length=2000)
    findings: list[Finding] = Field(max_length=12)
    missing_information: list[str] = Field(max_length=12)
    conflicting_evidence: list[str] = Field(max_length=12)
    uncertainty: list[str] = Field(max_length=12)
    recommended_review_actions: list[str] = Field(max_length=12)
    abstained: bool
    scope: Literal["evidence_review", "outside_scope"]


class Source(StrictContract):
    evidence_id: str
    version: int
    digest: str
    citation: str
    quality_state: str


class ClinicalEvidenceReviewPacket(StrictContract):
    run_id: str
    patient_id: str
    clinical_question: str
    summary: str
    findings: list[Finding]
    missing_information: list[str]
    conflicting_evidence: list[str]
    uncertainty: list[str]
    recommended_review_actions: list[str]
    source_references: list[Source]
    prevention_window: dict | None = None
    grounding_status: Literal["source_references_validated", "partially_grounded",
                              "insufficient_evidence", "conflicting_evidence", "validation_failed"]
    requires_human_review: Literal[True] = True
    abstained: bool
    origin: Literal["model", "system_abstention"]
    model_name: str
    created_at: str


class Review(StrictContract):
    decision: Literal["approve_summary", "reject", "request_evidence"]
    note: str = Field(min_length=1, max_length=500)
