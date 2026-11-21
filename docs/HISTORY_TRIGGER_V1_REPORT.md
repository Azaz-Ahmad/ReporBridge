# Historical trigger release — history-trigger-v1

## Result and baseline

GO for this synthetic demonstration: final SQLite **312/312**, PostgreSQL **312/312**, React **78/78**, build passed, smoke **12/12**, artifact-tool checks **2/2**, final PostgreSQL browser journeys **1/1 each**, and **10/10 consecutive fresh SQLite browser journeys**, with zero logged server/lock exceptions. No Playwright test retries or skips in the final journeys. Clinical confirmation remains pending; this is not a clinical system.

Started from latest passing release **action-v1**, commit `cddde7d1c697aa4e74e39034ce7c1ea1366a26e2`; the unmerged ui-v1 restyle is excluded. Branch `feat/history-trigger`. No push, merge, dependency changes, tag moves or history rewriting.

## Stage 0 — existing behavior (reported before changes)

At the baseline, `backend/app/history.py:view` linked a historical rule trace to existing open obligations; `backend/app/history_policy_v1.json` required an open PRE obligation. `backend/app/service.py:register_pregnancy` created the standard pregnancy coordination obligation, not a separate obligation from the Hospital A finding. Thus the earlier finding supplied a rule link, not a newly identified candidate.

## Implemented behavior

* A new data file, `backend/app/historical_relevance_policy_v1.json`, defines the exact source/finding match, eligibility wording, rule/version, Reviewer owner, W1 reference and ordinary lifecycle rule. No age/year/risk inference. A documented PCOS diagnosis remains synthetic policy test data and pending clinical confirmation.
* Pregnancy registration and authorized earlier-source M08 arrivals evaluate those data predicates. One separately persisted **Candidate: needs clinician confirmation** is created per patient/transition/rule/version, including pinned trigger and supporting document versions, hashes, facilities, authenticated source links and calculator context. A nonmatching patient gets none. Replays are idempotent.
* Existing patient-scoped grants protect every candidate read/decision. Only the existing Reviewer role can confirm or dismiss, with a required rationale. Confirmation creates a **distinct ordinary open obligation** owned by Reviewer. Confirmation alone neither approves clinical completion nor closes care; the unchanged agent/review/evidence/dependency/closure sequence is required.
* Invalidated or superseded pinned trigger evidence withdraws the candidate. For an already confirmed obligation, the detector invalidates its synthetic workflow confirmation through the existing M08 path: existing closure reconsideration reopens care and blocks closure. Original sources and decisions remain auditable.
* Candidate creation/review/withdrawal appear in the activity feed, global audit and patient detection timeline with the session demo-calendar date. Original UTC audit recording timestamps remain intact. Dashboard badge and candidate passport show trigger evidence, simulated facilities, rule/version, eligibility, Reviewer ownership and current server-calculated W1. Clinical citation displays **pending clinical confirmation**.
* The candidate card reuses the existing explicit, attested earlier-source investigation endpoint. The unchanged seven read-only M08 tools and grounding validator constrain it to cited evidence. Controlled-provider tests verify tool use and reject claims of risk, clinical relevance or confirmation/closure recommendations without altering candidate/obligation state. No live model generation was requested or claimed in this task; accepted existing real-response replays remain on the existing paths.
* Additive migration **0010**, after 0009, adds only the separate candidate table; existing clinical table definitions remain untouched. Readiness now expects 0010. Strict synthetic reset validation archives attested candidates and their ordinary lifecycle fixtures.
* A bounded regression reproduced SQLite requests timing out while competing for `BEGIN IMMEDIATE`. A standard-library, reentrant in-process queue now surrounds the original transaction and commit/rollback scope. The original database lock, PostgreSQL advisory lock, authorization, synchronization and clinical operations are unchanged. The red/green test also verifies rollback and release after an exception. No timeout increase or request retry was added.

## Tests — every JUnit invocation

Counts are per invocation, not a cumulative unique-test count. The full backend grew from 291 to 311 with candidates, then to 312 with the concurrency regression; React grew from 65 to 78. Parametrized tests count as separate cases.

| Invocation | Passed | Failed | Setup/other errors | Skipped | Evidence |
|---|---:|---:|---:|---:|---|
| postgres-healthy | 311 | 0 | 0 | 0 | `test-reports/history-trigger-v1/postgres-healthy.xml` |
| queue-green | 21 | 0 | 0 | 0 | `test-reports/history-trigger-v1/queue-green.xml` |
| queue-red | 0 | 1 | 0 | 0 | `test-reports/history-trigger-v1/queue-red.xml` |
| stage1-backend | 77 | 1 | 0 | 0 | `test-reports/history-trigger-v1/stage1-backend.xml` |
| stage1-final-backend | 77 | 1 | 0 | 0 | `test-reports/history-trigger-v1/stage1-final-backend.xml` |
| stage1-verified-backend | 78 | 0 | 0 | 0 | `test-reports/history-trigger-v1/stage1-verified-backend.xml` |
| stage2-final-react | 75 | 0 | 0 | 0 | `test-reports/history-trigger-v1/stage2-final-react.xml` |
| stage2-react | 73 | 0 | 0 | 0 | `test-reports/history-trigger-v1/stage2-react.xml` |
| stage3-backend | 83 | 1 | 0 | 0 | `test-reports/history-trigger-v1/stage3-backend.xml` |
| stage3-final-backend | 84 | 0 | 0 | 0 | `test-reports/history-trigger-v1/stage3-final-backend.xml` |
| stage3-react | 77 | 0 | 0 | 0 | `test-reports/history-trigger-v1/stage3-react.xml` |
| stage3-verified-backend | 85 | 0 | 0 | 0 | `test-reports/history-trigger-v1/stage3-verified-backend.xml` |
| stage3-verified-react | 78 | 0 | 0 | 0 | `test-reports/history-trigger-v1/stage3-verified-react.xml` |
| original-combined-sqlite | 311 | 0 | 0 | 0 | `test-reports/20261121-153440-bc5d0e08/sqlite.xml` |
| original-combined-postgres | 305 | 0 | 6 | 0 | `test-reports/20261121-153440-bc5d0e08/postgres.xml` |
| original-combined-components | 78 | 0 | 0 | 0 | `test-reports/20261121-153440-bc5d0e08/components.xml` |
| final-combined-sqlite | 312 | 0 | 0 | 0 | `test-reports/20261121-165235-2ea65f62/sqlite.xml` |
| final-combined-postgres | 312 | 0 | 0 | 0 | `test-reports/20261121-165235-2ea65f62/postgres.xml` |
| final-combined-components | 78 | 0 | 0 | 0 | `test-reports/20261121-165235-2ea65f62/components.xml` |

Six successful TypeScript/Vite build invocations: four stage build logs and two combined regression build logs. Release artifact tests: one invocation, **2 passed**. Smoke: two invocations, **12 passed each**; first **6734 ms**, final **9390 ms**, zero live generation requests in either. The existing authenticated model-catalog probe is read-only.

### Browser invocations and preserved failures

| Invocation | Passed | Failed | Notes |
|---|---:|---:|---|
| history-trigger-stage3 | 0 | 1 startup job | Zero test cases started: health expected old migration 0009 while scratch DB was at 0010. Fixed readiness; added regression. |
| history-trigger-stage3-ready | 1 | 0 | Full journey passed after readiness correction. |
| Combined PostgreSQL browser | 1 | 0 | Existing exported FHIR validation passed. |
| Combined PostgreSQL replay | 0 | 1 | New closure UI assertion ran before the slow successful response; artifact retained. |
| pg-verified-1 | 1 | 0 | Successful closed response asserted before unchanged UI assertion; exported FHIR validation passed. |
| pg-verified-2 | 1 | 0 | Same corrected journey and FHIR validation. |
| history-trigger-v1-release-10 | 10 | 0 | All assertions passed, but run04 logged two SQLite lock exceptions while the full PostgreSQL suite was running. Preserved. |
| history-trigger-v1-isolated-10 | 10 | 0 | All assertions passed, but run07 logged two lock exceptions without a concurrent suite; preserved and followed by the queue fix. |
| Final combined PostgreSQL browser | 1 | 0 | Full lifecycle and FHIR validation after the SQLite queue fix. |
| Final combined PostgreSQL replay | 1 | 0 | Full repeated lifecycle and FHIR validation. |
| history-trigger-v1-queue-fixed-10 | 10 | 0 | Ten fresh SQLite profiles/databases after the queue fix; no server/lock exceptions, Playwright retries, skips or flaky results. |

The original combined run is **not** reported as clean: PostgreSQL recorded **305 passed / 6 setup errors**, because Docker Desktop and PostgreSQL were unavailable at its start. The existing Docker service and persistent container were started without recreation, image pull or data reset. A read-only SELECT then succeeded in 0.281 s; the subsequent complete PostgreSQL suite passed 311/311, followed by the final post-queue suite at 312/312. The configured application schema was neither migrated nor reset: all migration/reset tests used isolated SQLite files or PostgreSQL schemas.

The PostgreSQL replay failure trace shows a successful close POST taking **5035.985 ms**, beyond the default 5000 ms UI assertion wait. The UI correctly showed a disabled pending action. The fix changes only the **newly added** closure step to wait for its exact POST, assert success and JSON status `closed`, then run the same “Closure verified” assertion. No app behavior, timeout or existing assertion was weakened. Original browser assertions remain intact; new assertions cover candidate identification, confirmation, independent closure gates, invalidation/withdrawal/reopening and unchanged windows. No existing React/backend assertions were changed.

Other preserved failures: the first two Stage 1 backend invocations each had **77 passed / 1 failed** because the new reset fixture mixed noncanonical dating setup with strict TSP reset. The fixture now uses the canonical TSP seed; the reset assertion and guard were retained. One attempted helper edit failed with a Python quoting SyntaxError before changing files. One later red-test launcher used the wrong relative interpreter path and executed **zero tests**; the corrected failing test is retained in queue-red.xml/log. Stage 3 initially had **83 passed / 1 failed**: a new FHIR regression exposed candidate M08 references in legacy standalone Task provenance. Candidate-only audit events now remain outside Task provenance, while their authenticated M08 citations remain in the candidate/global audit. The FHIR validator was retained; the corrected focused suites and full suites pass.

An additional final-report guard caught two `BEGIN IMMEDIATE` SQLite lock exceptions in run04 of the first 10/10 sequence, despite all browser assertions passing. They affected the candidate read and existing historical-handoff read, before their domain operations began. The guard stopped report generation; it was not bypassed. A second isolated ten-journey sequence also passed every assertion but logged two lock exceptions in run07, in the history and coordination reads. Thus concurrent PostgreSQL work was not a sufficient explanation. Both complete sequences/logs remain intact. An earlier progress update incorrectly stated no lock errors before the complete log audit; it was corrected.

Requests were contending for the same SQLite writer transaction and could exceed its lock-acquisition timeout before domain code ran. A bounded regression with a 30 ms SQLite busy timeout and a held first transaction reproduced the exact failure (**0 passed / 1 failed**, `queue-red.xml`). The fix queues local writers before opening the transaction, using `threading.RLock`, with no timeout increase or retry and the original transaction/clinical body unchanged. The same regression plus candidate tests passed **21/21** (`queue-green.xml`), proving serialized commits, rollback, and release after failure. Full regression was repeated on this frozen fix: SQLite312, PostgreSQL312, React78, build, two PostgreSQL journeys, smoke12, then a third consecutive ten-journey sequence passed with zero logged server/lock exceptions. This is an app transaction-queue fix, separate from the earlier browser acknowledgment wait fix.

All original logs/XML/JSON and the complete failed replay trace/context are retained under `test-reports/history-trigger-v1/`, `test-reports/20261121-153440-bc5d0e08/`, final full suite `test-reports/20261121-165235-2ea65f62/`, and `test-reports/release/history-trigger-*`. In particular: `preserved-pg-browser-replay-failure/` and `pg-browser-failure-timing.json`. Credential redaction preserves assertions, timing, images and failure context.

## Guardrails verified and known limits

The protected window calculator/policy, history policy/grounding, investigation workflow, seven M08 tool contracts, authorization and core closure functions are unchanged from action-v1. Package dependencies and existing migrations are unchanged. Actual model output is not used to identify candidates or decide care. Existing tags were verified unchanged. Source hashes bind final tests to the released implementation.

This is exact policy-data matching, not medical interpretation or a validated clinical recommendation. Clinical policy values and citations remain pending clinical confirmation. Candidates do not become active care or FHIR Tasks before human confirmation. Missing/uncertain dating does not invent W1; the existing calculator remains authoritative. Completing this separate review does not alter existing PRE-based calculator semantics.

Dismissed/withdrawn candidates are terminal for the same episode/rule version; automatic reactivation is not implemented. Confirmed-source withdrawal reopens ordinary care through existing M08 gates; automatic recovery/reconfirmation is not implemented. There is no unscoped historical backfill or creation on GET. Existing patient grants and the canonical synthetic Amira investigation attestation remain required; grants are not automatically added. The standalone FHIR export's source scope remains unchanged. Apply migration0010 before running this branch against the configured app database; it was deliberately not applied to that database by this task.

The local SQLite queue covers threads in one app process; multi-process/multi-worker SQLite scaling was not verified. Existing database-level locking remains in place. PostgreSQL retains its original advisory transaction lock and passed its full suite and browser runs.

## Files changed

* `backend/app/clinical/api.py`
* `backend/app/clinical/events.py`
* `backend/app/demo.py`
* `backend/app/historical_candidates.py`
* `backend/app/historical_candidates_api.py`
* `backend/app/historical_candidates_schema.py`
* `backend/app/historical_relevance_policy_v1.json`
* `backend/app/history.py`
* `backend/app/history_api.py`
* `backend/app/main.py`
* `backend/app/service.py`
* `backend/migrations/env.py`
* `backend/migrations/versions/0010_historical_candidates.py`
* `backend/tests/test_historical_candidates.py`
* `backend/tests/test_sqlite_write_queue.py`
* `frontend/e2e/journey.spec.ts`
* `frontend/src/App.tsx`
* `frontend/src/HistoricalCandidates.test.tsx`
* `frontend/src/HistoricalCandidates.tsx`
* `frontend/src/History.tsx`
* `frontend/src/Jury.tsx`
* `frontend/src/Tsp.tsx`
* `frontend/src/screens.tsx`
* `frontend/src/showcase.tsx`
* `frontend/src/style.css`
* `frontend/src/types.ts`
* `docs/HISTORY_TRIGGER_V1_REPORT.md`

This report is also committed as `docs/HISTORY_TRIGGER_V1_REPORT.md`. Browser-generated replacements of the two legacy dashboard PNGs were preserved in ignored test artifacts and restored, so they are not part of this change.
