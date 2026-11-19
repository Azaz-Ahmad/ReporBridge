# v0.6 increment 1 implementation

**GO for the local synthetic prevention-decision increment.** Persisted decisions, patient/reviewer authorization, deterministic timing, trusted agent retrieval, independent clinical recording, all five screens, demo reset and regression gates passed.

The starting commit is 1a12155f2727aef9fbcd87fad8ff7a7e34f46b1e. The ending commit is reported in the delivery message and git log -1.

## Implemented domain

Migration 0006 adds prevention_decisions, prevention_prerequisites, prevention_timing_policies, prevention_decision_records and prevention_decision_audit. Existing records and migrations were preserved. The live upgrade backed up PostgreSQL and verified all 22 prior tables unchanged.

Decision fields include canonical patient, linked obligation, rationale, owner, source evidence, required evidence definitions/status, lifecycle, versioned rule/policy, optional due date, immutable reviewer outcome, structured source snapshot and audit.

Lifecycle states are awaiting_evidence, ready_for_review, under_review, decided, escalated and cancelled. Revision/snapshot checks invalidate stale review. Unique immutable records and serialized transactions protect concurrent recording. Reviewed evidence, clinician outcome, initiated follow-up and verified obligation closure have separate audit events.

The illustrative registry supports the preconception metabolic review. Other obligation rules are rejected until an appropriate registry is provided. Document/record availability supports review; clinical sufficiency is attested by the reviewer.

Only a patient-authorized reviewer records an outcome. Reconciled requires available prerequisite categories and supporting current evidence from each category. Deferral/follow-up can explicitly record unresolved evidence. These records never authorize the original clinical obligation closure.

## Timing and fixture

Amira has one linked prevention decision and no deadline. The UI displays Timing not established. The canonical pregnancy journey was preserved.

A separate demo-prevention-timing patient has two explicitly illustrative policies/decisions for due-soon and overdue display. No clinical deadline or diagnostic threshold was invented. Backend counts and labels derive from registered policy state and current UTC time. Retirement or supersession removes effective timing.

The canonical reset archives its decision history, restores a new starting decision and preserves unrelated patients, the timing scenario and independent M08 source feed.

## Agent and APIs

The existing Gemini/OpenRouter provider, six graph nodes and seven M08 tools are reused. A coordinator initiates a bound readiness investigation with only a request ID. Backend patient/decision context, current prerequisites and snapshot guard the investigation. The agent cannot change a policy, prerequisite, clinical decision, approval or closure.

A real run is retained in the running app with actual source-linked findings and tool trace. It found conflicting evidence, abstained and entered human review. Usage and both model identifiers are persisted. The earlier rejected run remains visible as a safe system abstention.

The versioned prevention API supports scoped snapshots/reads, creation, lifecycle transitions, reviewer recording, follow-up initiation, illustrative policy creation/state/assignment, decision-bound investigation listing/execution and the separate timing fixture. See V06_DECISION_DATA_CONTRACT.md for method/path/role details.

## Five visible screens

Population shows the Prevention Decision Queue with backend counts and patient links. Workspace shows a chronological Decision Timeline with life-stage context, owner, evidence readiness, timing and recorded outcome when present. Passport shows prerequisites, source/rule provenance and reviewer controls. Care-resolution shows the bound investigation alongside both established workflows. Evidence & audit shows persisted Decision History.

The six original innovation cards, clinical timeline, dependency graph, source explorer, passport, deterministic care-resolution, evidence-specific approval, closure verification, FHIR export and reset remain functional.

## Verification and screenshots

Final regression passed 110 Python tests on PostgreSQL, 110 on SQLite, 16 React tests, the production build, both Playwright journeys and both FHIR download validators. Browser scenarios include a reviewer recording a decision and initiating follow-up while clinical approval/closure remain unsatisfied.

The actual readiness run used six model calls and five M08 tool executions. It preserved the existing clinical snapshot and returned conflicting_evidence with mandatory human review.

Screenshot files are 01-dashboard.png, 02-workspace.png, 03-passport.png, 04-resolution.png, 05-audit.png and 06-mobile-passport.png under docs/screenshots/v06. All were inspected and all five screens fit at 390 pixels after the expanded-agent layout fix.

## Remaining scope

The registry and all timing examples are illustrative. Named staff identity, approved clinical timing rules, additional clinical pathways, scalable/background evaluation and owner reassignment UI require further work. Narrative interpretation remains human-reviewed. Details are in V06_REMAINING_LIMITATIONS.md.
