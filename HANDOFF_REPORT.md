# Simulated facility handoff v1

**GO for the local synthetic demonstration only.** Base: passing TSP commit `9ef56af` / `tsp-v1`. Branch: `feat/simulated-handoff`; annotated release tag: `handoff-v1`. Three implementation stages were tested and committed separately. No merge, remote push, force-push or history rewriting.

## Delivered and files changed
- `backend/app/handoff.py`, `handoff_api.py`: separate `demo-handoff` patient; Hospital A origin and Hospital B receiving facility; pregnancy-before-receipt check; idempotent receipt; original/responsible-owner history; origin invalidation through the existing event processor.
- `backend/app/handoff_provenance.py`, `clinical/gateway.py`: read-only facility/receipt metadata in the existing provenance dictionary. Source resources retain their hash, version and lineage.
- `backend/app/main.py`: scoped route registration and simulated facility agents in generated FHIR Provenance.
- `frontend/src/Handoff.tsx`, `ClinicalExplorer.tsx`, `screens.tsx`, `App.tsx`, `style.css`: SIMULATED labels, receive action, owner history, passport/explorer/timeline chips and query refresh after pregnancy/closure.
- Tests: `backend/tests/test_handoff.py`, `frontend/src/Handoff.test.tsx`, `frontend/e2e/journey.spec.ts`.

Existing fields fit: Encounter.serviceProvider and Observation.performer/DocumentReference.author use display-only Organization references; Encounter.identifier persists stable simulated facility identifiers. Standalone Organization ingestion was not added. Existing evidence versions, receipts and audit history store transport/source/receipt details. **No migration, facility column or dependency was needed; schema remains 0008.**

M08 contracts, authorization code, closure gates, grounding rules, TSP calculator and model tools are unchanged. The fixture explicitly adds a reviewer patient grant once; it never restores a revoked grant. Viewers receive no grant. Hospital labels are not an authorization boundary. Agents have no handoff write tools and never compute timing, eligibility or closure.

## Exact verification invocations
Counts are per invocation, not cumulative unique coverage. XML/JSON artifacts remain in ignored `test-reports/`.

| Invocation | Actual result |
|---|---|
| `handoff-stage1.xml` | 3 passed |
| `handoff-stage2.xml` | 48 passed, 4 failed |
| `handoff-stage2-retry.xml` | 51 passed, 1 failed |
| `handoff-stage2-final.xml` | 53 passed |
| Frontend build #1 | Passed |
| `handoff-stage3-components.xml` | 33 passed |
| Frontend build #2, after refresh/browser wiring | Passed |
| `handoff-stage3-final-components.xml` | 33 passed |
| `handoff-full-sqlite.xml` | 217 passed, 0 failed/errors/skips; 216.31 s |
| `handoff-full-postgres.xml` | 217 passed, 0 failed/errors/skips; 477.71 s |
| `handoff-stage3-browser.json` | 1 passed, 0 unexpected/skipped/flaky; 69.56 s |

Full suites retain all 209 passing TSP backend tests plus eight handoff tests, and all 27 prior React tests plus six handoff tests. Browser coverage retains the original five-screen/TSP journey and adds receipt after pregnancy, chips/provenance/history, idempotency, approval without closure, verified closure, origin invalidation/reopening and 390 px layout. Downloaded Amira FHIR structure/reference validation passed. Handoff FHIR/provenance and grant-denial tests passed in both backend suites. No live LLM requests were made.

Failures are preserved under their original filenames. First Stage 2 failure: M08 rejected identifier-only Organization references (`logical_reference: Use a canonical literal reference in this scope.`). Supported display-only references and Encounter identifiers resolved it without relaxing validation. Retry failure: the new patient correctly lacked reviewer access; an explicit fixture-only grant resolved it while preserving access checks. A separate test confirms reseeding does not restore revoked access.

## Local runtime and limits
The existing local backend was restarted and the separate handoff fixture seeded/registered/received. It shows Hospital A origin, Hospital B responsible team, original owner retained, actual receipt date and an open obligation. Replay is stable; an ungranted viewer gets 404. All 16 checked patient-scoped tables for Amira/TSP uncertain-dating remained hash/count-identical. Proof: `handoff-runtime-smoke.json`; aggregate gates: `handoff-release-summary.json`.

This is one-process, local **SIMULATED** exchange, not a live institutional integration, authenticated external sender or facility tenancy system. Organization displays are synthetic provenance labels; source invalidation is a coordinator-triggered simulation using unchanged correction gates. Seed is idempotent and preserves invalidation/history; it is not a reset or automatic requalification of invalidated evidence. No real patient data, clinical interpretation, eligibility logic, timing changes or secret material was added. Existing TSP clinical defaults/citation remain pending confirmation.
