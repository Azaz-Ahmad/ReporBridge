# History handoff release report

Release: **GO for the bounded synthetic demo**, not a clinical or production release.
Branch: `feat/history-handoff`. Source implementation: `7fbc53d`; annotated release tag: `history-handoff-v1` on this report commit. Base: `0a2f9fa` (passing dashboard release). No merge, push or history rewrite. Existing `handoff-v1` preserved.

## Implemented

- Migration **0009** adds patient-scoped facility annotations without changing clinical evidence payloads/digests. Applied locally; before/after manifests verified all **28 existing tables** unchanged by migration. A pre-migration database backup and manifest are retained under ignored `test-reports/`.
- Clearly labelled **Simulated provider exchange**, Hospital A to Hospital B, uses the existing idempotent clinical event processor and unchanged patient grants. Origin facility, receipt date, source version and provenance remain visible. No live hospital connection.
- Seed JSON holds the replaceable historical finding and source document, dated **2017-07-10**. Existing Amira identity/calendar preserved: DOB 1995-04-12, age **22** at the earlier record and **31** at pregnancy registration (2026-11-08). No new glucose values or clinical thresholds.
- A separate versioned JSON rule matches the literal historical finding and an existing open PRE obligation/pregnancy context to the existing **W1** result. Trace includes source IDs, policy version/hash and the unchanged citation **CITATION_PENDING_CLINICAL_CONFIRMATION**. It remains **pending clinical confirmation**. No timing calculation or clinical criteria were added to Python.
- Workspace and Passport show “Found in earlier records”, facility chips, date, version-pinned authorized source/document viewer and pending rule trace. Receipt and ordinary clinical/clock changes refresh history; previous explanations clear when their context changes. Existing TSP badge/calculator/demo clock behavior retained.
- Existing A01 agent explains only cited source literals and the trusted server-rendered rule. Same six-node workflow and seven M08 tools; no model fallback added. Added risk/relevance/eligibility claim rejection and history-only permitted narrative messages, on top of existing source/value/citation grounding. Stale source/policy/window context blocks review. Human approval and qualifying evidence still do not bypass explicit closure gates.

## Files changed

22 implementation/test files plus this report:

- Backend: `app/history.py`, `history_api.py`, `history_guard.py`, `history_seed_v1.json`, `history_policy_v1.json`, `record_facilities.py`, `clinical/gateway.py`, `main.py`; investigation `contracts.py`, `graph.py`, `grounding.py`, `service.py`.
- Database: `backend/migrations/env.py`, `backend/migrations/versions/0009_record_facilities.py`.
- Tests: `backend/tests/test_history.py`, `frontend/src/History.test.tsx`, `frontend/e2e/journey.spec.ts`.
- Frontend: `src/History.tsx`, `App.tsx`, `Tsp.tsx`, `screens.tsx`, `style.css`.

Backend app paths above are under `backend/`; frontend src paths are under `frontend/`. No new dependencies or credentials committed.

## Verification

Final full suites: **238/238 SQLite**, **238/238 PostgreSQL**, **41/41 React**, **1/1 browser journey**, zero failures/skips. Frontend production build passed after the final UI changes. The final subsequent change was backend history-policy/guard refinement; its 60 focused checks and both full backend suites passed.

Backend tests cover authorization denial, immutable facility/provenance, replay idempotency, deterministic rule/source trace, no matching-record trigger, seed-only finding replacement, real local M08 tool invocation through a scripted model double, unsafe-risk output rejection, unbound context abstention, policy staleness and approval/evidence/closure sequencing. Existing correction/reopening regressions remain in the full suites.

The browser covers receipt/source/document/rule UI, the existing review/closure flow, unchanged source hashes and mobile overflow. The new historical closure phase uses existing authenticated APIs to supply qualifying evidence, approve and explicitly close; it does not pretend those steps were all manual UI actions. Existing legacy UI review coverage remains. FHIR export/reference validation passed on the successful browser invocations.

No live LLM calls were made. Model tests use scripted output with actual local authorized M08 retrieval. This release establishes bounded explanation safety and orchestration, not live-provider quality or clinical certification.

Exact invocation ledger (each XML is a distinct invocation; intermediate runs are not final-release counts):

| Artifact in test-reports/ | Tests | Failures | Errors | Skips |
|---|---:|---:|---:|---:|
| history-final-components.xml | 41 | 0 | 0 | 0 |
| history-full-postgres.xml | 235 | 0 | 0 | 0 |
| history-full-sqlite.xml | 235 | 0 | 0 | 0 |
| history-narrative-gate.xml | 60 | 0 | 0 | 0 |
| history-release-components.xml | 40 | 0 | 0 | 0 |
| history-release-postgres.xml | 238 | 0 | 0 | 0 |
| history-release-sqlite.xml | 238 | 0 | 0 | 0 |
| history-stage1.xml | 9 | 0 | 0 | 0 |
| history-stage2-final.xml | 4 | 0 | 0 | 0 |
| history-stage2.xml | 31 | 0 | 0 | 0 |
| history-stage3-components.xml | 40 | 0 | 0 | 0 |
| history-stage4-components.xml | 40 | 0 | 0 | 0 |
| history-stage4-final.xml | 53 | 0 | 0 | 0 |
| history-stage4-release.xml | 55 | 0 | 0 | 0 |
| history-stage4.xml | 52 | 0 | 0 | 0 |
| history-stage5-focused.xml | 17 | 0 | 0 | 0 |

| Browser artifact | Passed | Failed | Skipped |
|---|---:|---:|---:|
| history-browser.json | 0 | 1 | 0 |
| history-browser-retry.json | 0 | 1 | 0 |
| history-browser-final.json | 1 | 0 | 0 |
| history-browser-release.json | 1 | 0 | 0 |

Four frontend build invocations passed during UI stages/final UI verification; builds have no test count.

Failures preserved, not overwritten: the first browser run timed out awaiting reset feedback while its request was pending; the journey now awaits and checks the response before asserting feedback. The second run could not see the historical finding after successful receipt; the UI now cancels an obsolete GET and applies the authoritative receipt response immediately before revalidation. Original reports and copied screenshots/traces remain in `history-browser-failed-artifacts/` and `history-browser-retry-failed-artifacts/`. Both subsequent full browser runs passed. All XML/JSON reports are ignored local artifacts, not committed secrets or generated bulk.

Final restarted local PostgreSQL application reports ready. `history-release-runtime-smoke.json` confirms two historical sources, ages 22/31, a pending W1 trace, **IN_WINDOW**, clinical work open and no LLM calls. The demo remains open for presentation; closure tests use isolated databases.

## Known gaps and semantic boundaries

- Hospital A/B exchange is one synthetic scenario, not a real provider network, external identity federation or institution authorization system. Existing patient-scoped access is unchanged.
- The historical source is associated with the existing current open PRE review obligation. Original obligation creation/audit timestamps and original source are not rewritten or backdated to 2017.
- No matching source means no trigger from this additional historical rule. Other existing carried-obligation rules may independently produce W1; this feature does not suppress them.
- Changing the seed finding alone changes the matching result; a different authorized clinical mapping also requires clinician-reviewed policy data. PCOS is a quoted historical placeholder, not a current diagnosis or risk assessment.
- Policy/citation need clinical confirmation. No clinical certification, live-model evaluation or production-readiness claim. Conservative narrative constraints intentionally abstain when wording cannot be grounded; agents cannot change windows, eligibility, relevance or closure.
