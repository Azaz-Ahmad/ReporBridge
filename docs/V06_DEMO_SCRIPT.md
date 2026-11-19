# v0.6 demonstration

Open http://127.0.0.1:5173 and sign in with the existing local coordinator token. The running Amira journey remains at pregnancy with its original obligations. The linked prevention decision shows conflicting assessment evidence and Timing not established.

1. Open Population dashboard. Inspect the Prevention Decision Queue and its backend-derived counts. The separate Illustrative Timing Scenario demonstrates due-soon/overdue states.
2. Select Amira's decision link. Passport shows the owner, rationale, prerequisites, current source IDs, rule, timing provenance and decision lifecycle.
3. Open patient evidence in the workspace. The Decision Timeline includes actual life-stage events, decision creation, owner and prerequisite evaluations. The original life-stage timeline and dependency graph remain visible.
4. Open decision readiness investigation in Care-resolution center. The retained real Gemini run shows actual tools, citations, structured values, conflicts, abstention and pending human review. Confirm the original Clinical Evidence Investigation and deterministic care-resolution panels remain available.
5. As a reviewer, open Passport and enter a review rationale. Select Begin clinician review. Inspect source records and choose an outcome. A reconciled outcome requires available evidence and support for every prerequisite. With unresolved conflicts, record deferral or follow-up with an appropriate rationale and follow-up action.
6. Explicitly confirm review of the current snapshot and select Record clinical decision. This records the reviewer outcome in its own table.
7. As coordinator, select Initiate follow-up for a recorded action. Evidence & audit shows retrieval, review, decision and follow-up as separate persisted events.
8. The clinical obligation still requires its established qualifying completion evidence, evidence-specific approval and verified closure workflow.
9. Reset Amira only when a fresh demonstration is desired. Prior decision history is archived, a fresh decision is linked to the reset obligation, and the separate timing patient remains intact.

Reviewer recording in the browser test uses disposable synthetic data. The live app retains the readiness packet for a human reviewer and has no automatically recorded clinical decision.

## Repeatable verification

From F:\ReproBridge run scripts\Test-Demo.ps1 -PostgreSQL. It runs both databases, React tests, the production build and two independent PostgreSQL Playwright journeys. Browser tests disable paid model calls and exercise the original clinical journey plus reviewer decision recording, follow-up, reset isolation and timing display.

A live readiness request uses POST /api/v1/prevention/decisions/{id}/investigations with a fresh request_id. Keep all data synthetic. Source changes or an invalid packet cause abstention.

Screenshots of all five actual screens are in docs/screenshots/v06. They include the live provider tool trace and the separately labeled timing scenario.
