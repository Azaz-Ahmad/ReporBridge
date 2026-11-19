# Prevention decision contract

The canonical patient is derived from the linked obligation. Caller-supplied patient identity, actor and clinical timestamps are excluded from creation and reviewer-recording bodies. All endpoints use existing bearer-role authentication and patient grants.

## Lifecycle

| Current state | Permitted operation | Result |
|---|---|---|
| awaiting_evidence | Deterministic availability evaluation | ready_for_review when all prerequisites are available for review |
| ready_for_review | Relevant source/policy change | awaiting_evidence or refreshed ready_for_review |
| awaiting_evidence, ready_for_review, escalated | Reviewer begins review | under_review |
| under_review | Source or policy changes | Review invalidated and technical readiness reevaluated |
| under_review | Authorized reviewer records outcome | decided |
| awaiting_evidence, ready_for_review, under_review, escalated | Coordinator/reviewer escalates or cancels | escalated or cancelled |
| escalated | Coordinator/reviewer resumes | Derived technical readiness |
| decided, cancelled | New outcome attempt | Rejected. A new review requires a new decision |

Transitions require current revision and rationale. Recording additionally requires the exact reviewed snapshot hash. Outcomes are reconciled, deferred, follow_up_required and not_applicable. Reconciled requires available prerequisites and cited support from every required category. Deferral/follow-up may explicitly record unresolved evidence. Follow-up-required outcomes need at least one action.

The reviewer identity is the authenticated demo reviewer role. The server supplies decision timestamp, rule/policy reference and immutable evidence snapshot. Staff-level identities require future authentication integration.

## API

All paths below are under /api/v1/prevention.

| Method | Path | Role |
|---|---|---|
| GET | /snapshot?patient_id=... | Scoped reader |
| POST | /decisions | Coordinator |
| GET | /decisions/{id} | Scoped reader, including archived history |
| POST | /decisions/{id}/transition | Coordinator/reviewer, with reviewer required to begin review |
| POST | /decisions/{id}/record | Reviewer |
| POST | /decisions/{id}/follow-up/{index} | Coordinator |
| POST | /policies | Coordinator, illustrative policies only |
| POST | /policies/{id}/state | Coordinator |
| POST | /decisions/{id}/policy | Coordinator |
| GET | /decisions/{id}/investigations | Scoped reader |
| POST | /decisions/{id}/investigations | Coordinator |
| POST | /demo/timing | Coordinator |

CreateDecision contains obligation_id, owner, rationale and optional registered policy_id. The current registry supports the illustrative preconception metabolic review.

RecordDecision contains revision, reviewed_snapshot, outcome, rationale, M08 evidence_refs and follow_up. Unknown, unavailable or foreign source references fail closed. Immutable records and revision checks reject repeated or concurrent outcomes after the first commit.

DecisionInvestigationRequest contains only request_id. The backend supplies patient, decision binding, obligation and prerequisite context. Body parameters cannot replace patient scope or authorization.

## History semantics

review_started captures opening the review workflow. evidence_reviewed records explicit reviewer attestation to the current snapshot. decision_recorded captures the outcome. follow_up_initiated records a separate idempotent action. obligation_verified_closed observes the original clinical workflow's closure gate. Decision outcomes and AI summary reviews never write clinical approval or closure records.

Reset marks prior decisions archived and retains immutable outcomes/audit. A new canonical decision is created for the reset obligation. The original M08 source feed remains independently versioned.
