from datetime import datetime
from typing import Literal
from pydantic import Field, model_validator
from app.clinical.contracts import Contract, Identifier

RULE = "illustrative-metabolic-readiness@1.0.0"


class CreateDecision(Contract):
    obligation_id: Identifier
    owner: str = Field(min_length=1, max_length=160)
    rationale: str = Field(min_length=5, max_length=1000)
    policy_id: Identifier | None = None


class Transition(Contract):
    revision: int = Field(ge=1)
    action: Literal["begin_review", "escalate", "cancel", "resume"]
    rationale: str = Field(min_length=3, max_length=500)


class RecordDecision(Contract):
    revision: int = Field(ge=1)
    outcome: Literal["reconciled", "deferred", "follow_up_required", "not_applicable"]
    rationale: str = Field(min_length=5, max_length=1000)
    evidence_refs: list[Identifier] = Field(max_length=100)
    follow_up: list[str] = Field(max_length=10)
    reviewed_snapshot: str = Field(min_length=64, max_length=64)


class TimingPolicy(Contract):
    id: Identifier
    version: str = Field(min_length=1, max_length=40)
    due_at: datetime
    due_soon_seconds: int = Field(ge=0, le=31536000)
    illustrative: Literal[True]

    @model_validator(mode="after")
    def aware(self):
        if self.due_at.utcoffset() is None:
            raise ValueError("A due date requires a UTC offset.")
        return self


class PolicyState(Contract):
    status: Literal["retired", "superseded"]


class AssignPolicy(Contract):
    revision: int = Field(ge=1)
    policy_id: Identifier | None


class InvestigationRequest(Contract):
    request_id: Identifier
