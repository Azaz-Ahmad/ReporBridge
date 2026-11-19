"""Model drafts contain claims only; identity, scope and execution envelopes are backend owned."""
from typing import Literal
from pydantic import Field
from app.investigation.contracts import StrictContract, RunRequest, Draft, Finding, ClinicalEvidenceReviewPacket
from app.clinical.contracts import Identifier

class MultiRequest(RunRequest):
    decision_id: Identifier | None = None

class Relation(StrictContract):
    previous_id: str = Field(max_length=100)
    current_id: str = Field(max_length=100)

class TimelineFact(StrictContract):
    evidence_id: str = Field(max_length=100)
    clinical_time: str = Field(max_length=80)

class PrerequisiteFact(StrictContract):
    prerequisite_id: str = Field(max_length=100)
    status: Literal["missing", "unavailable", "conflicting", "requires_reconciliation", "available_for_review"]
    evidence_ids: list[str] = Field(max_length=16)

class ReconciliationDraft(Draft):
    conflicting_records: list[str] = Field(max_length=16)
    corrected_records: list[str] = Field(max_length=16)
    supersession_relationships: list[Relation] = Field(max_length=16)
    unresolved_discrepancies: list[str] = Field(max_length=8)

class ContextDraft(Draft):
    timeline_events: list[TimelineFact] = Field(max_length=16)
    linked_obligations: list[str] = Field(max_length=16)
    life_stage_transition_refs: list[str] = Field(max_length=16)

class GapDraft(Draft):
    prerequisites: list[PrerequisiteFact] = Field(max_length=16)
    unresolved_questions: list[str] = Field(max_length=8)

class UnifiedReviewPacket(ClinicalEvidenceReviewPacket):
    packet_complete: bool
    failed_agents: list[str]
    decision_id: str | None
    timing: dict
    timing_policy: dict | None
    prerequisites: list[dict]
    agent_sections: dict
    administrative_follow_up_proposals: list[str]
    trusted_context: dict

class AgentResult(StrictContract):
    run_id: str
    agent_id: Literal["A01", "A02", "A03", "A04"]
    patient_id: str
    task_objective: str
    state: Literal["not_selected", "pending", "running", "completed", "abstained", "failed"]
    findings: list[Finding]
    supporting_evidence_refs: list[str]
    uncertainty: list[str]
    abstained: bool
    validation_status: str
    model_identifier: str
    execution_metadata: dict
    validated_output: dict | None
    error: str | None
