"""Bounded requests and typed retrieval results shared by HTTP and tools."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

PatientId = Annotated[str, StringConstraints(pattern=r"^demo-[A-Za-z0-9.-]{1,59}$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")]
ResourceType = Literal[
    "Patient", "Observation", "Condition", "Encounter", "DiagnosticReport", "DocumentReference",
    "MedicationRequest", "MedicationStatement", "ServiceRequest", "CarePlan",
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Filters(Contract):
    kind: ResourceType | None = None
    status: str | None = Field(default=None, max_length=40)
    start: datetime | None = None
    end: datetime | None = None
    history: bool = False
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def interval(self):
        if any(value is not None and value.utcoffset() is None for value in (self.start, self.end)):
            raise ValueError("Provide times with UTC offsets.")
        if self.start and self.end and self.start > self.end:
            raise ValueError("Start must be on or before end.")
        return self


class Search(Filters):
    query: str = Field(default="", max_length=160)
    mode: Literal["structured", "document", "hybrid"] = "hybrid"


class SearchRequest(Search):
    patient_id: PatientId


class Event(Contract):
    source: Annotated[str, StringConstraints(pattern=r"^(workflow|synthetic-[A-Za-z0-9-]{1,50})$")]
    event_id: Identifier
    event_time: datetime
    version: int = Field(ge=1, le=2147483647)
    action: Literal["put", "invalidate"] = "put"
    resource: dict
    external_id: Identifier | None = None

    @model_validator(mode="after")
    def timestamp(self):
        if self.event_time.utcoffset() is None:
            raise ValueError("Event time must include a UTC offset.")
        return self


class Identity(Contract):
    namespace: Annotated[str, StringConstraints(pattern=r"^synthetic-[A-Za-z0-9-]{1,50}$")]
    external_id: Identifier


class EvidenceResult(Contract):
    id: str
    patient_id: str
    source: str
    kind: ResourceType
    resource_id: str
    version: int
    event_time: str | None
    clinical_time: str | None
    received: str
    status: str
    digest: str
    supersedes: str | None
    related_obligation_ids: list[str]
    provenance: dict
    normalized: dict
    quality: dict
    citation: str
    method: Literal["structured", "document"] = "structured"
    score: float | None = None
    section: str | None = None
    position: int | None = None
    content: str | None = None


class EvidencePage(Contract):
    items: list[EvidenceResult]
    next_offset: int | None
    outcome: Literal["found", "not_found"]


class ResourceResult(Contract):
    evidence: EvidenceResult
    resource: dict | None


class ResourcePage(Contract):
    items: list[ResourceResult]
    next_offset: int | None
    outcome: Literal["found", "not_found"]
