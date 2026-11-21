# action-v1 — coordination actions, guideline traceability and evidence correction

Branch: `feat/action-reopen`, from `release/demo-v1` (`2b33f16980a63c4213aa5f59b780f77e8f9306ee`), confirmed by the user. The unmerged `ui-v1` restyle is intentionally excluded. Existing tags remain unchanged. No merge or push.

Release decision: **GO for the synthetic demo**, with all requested final regression gates passing. Clinical policy values and guideline citation remain **pending clinical confirmation**. No production-readiness claim.

## Implemented

- `coordination_policy_v1.json` defines coordination-only action and responsible coordination role by returned window status. Completed states have no action; unknown states and unmatched policy versions produce none. The dashboard queue and passport display this server projection. It does not schedule, notify, create tasks, change the assigned owner, or instruct clinical treatment.
- The passport's Guideline traceability panel shows the pending-confirmation source label, actual active policy ID/version, eligibility text rendered using stored policy values, the historical rule and its actual server trace, and authorized supporting sources with facility, date, version and source links. Links use authenticated retrieval and exact evidence versions. The local source viewer resets when switching patients. Missing facilities are labelled as unrecorded. Hospital A/B provenance remains SIMULATED. The raw citation constant is not rendered in this panel.
- Evidence & audit includes “Simulate evidence correction (demo)”, only for DEMO_MODE coordinators and requiring a second explicit confirmation. The server independently requires a patient grant, a closed obligation, its recorded synthetic closing observation and the existing workflow source. It calls the unchanged M08 event processor with an invalidation; existing reconciliation reopens the obligation, retains its owner and records audit/lineage. The lifecycle strip shows the recorded reopening. No optimistic reopening or direct state/owner update is used.
- No migrations or dependencies were needed. The original window/timing policy, calculator, patient-window payload, closure gates, authorization implementation, seven M08 tools, grounding, model/replay code and agent workflows are unchanged. Agents never select these actions.

## Verification — exact invocations

| Invocation | Result | Evidence in repository |
|---|---|---|
| Stage 1 targeted backend | 38 passed; 0 failed/errors/skipped | `test-reports\action-v1\stage1-backend.xml` |
| Stage 1 React | 55 passed; 0 failed/errors/skipped | `test-reports\action-v1\stage1-react.xml` |
| Stage 2 targeted backend | 60 passed; 0 failed/errors/skipped | `test-reports\action-v1\stage2-backend.xml` |
| Stage 2 React | 56 passed; 0 failed/errors/skipped | `test-reports\action-v1\stage2-react.xml` |
| Stage 3 targeted backend | 65 passed; 0 failed/errors/skipped | `test-reports\action-v1\stage3-backend.xml` |
| Stage 3 React | 64 passed; 0 failed/errors/skipped | `test-reports\action-v1\stage3-react.xml` |
| Action-label fix React | 64 passed; 0 failed/errors/skipped | `test-reports\action-v1\stage3-action-label-react.xml` |
| Final patient-viewer isolation React | 65 passed; 0 failed/errors/skipped | `test-reports\action-v1\viewer-isolation-final-react.xml` |
| Full SQLite | 291 passed; 0 failed/errors/skipped | `test-reports\20261121-080239-735ad598\sqlite.xml` |
| Full PostgreSQL | 291 passed; 0 failed/errors/skipped | `test-reports\20261121-080239-735ad598\postgres.xml` |
| Full React | 64 passed; 0 failed/errors/skipped | `test-reports\20261121-080239-735ad598\components.xml` |
| Stage 1 / stage 2 / stage 3 / action-label fix / full-regression / final viewer-fix production builds | 6 separate successful builds | Stage 1 tool output; `test-reports/action-v1/*build.log`; full-run log |
| Corrected stage-3 SQLite browser journey | 1/1 passed | `test-reports/release/action-v1-stage3-corrected/` |
| Final PostgreSQL browser journey | 1/1 passed; downloaded FHIR R4 bundle validated | `test-reports\20261121-080239-735ad598/browser.json` |
| Final PostgreSQL browser replay | 1/1 passed; downloaded FHIR R4 bundle validated | `test-reports\20261121-080239-735ad598/browser-replay.json` |
| PostgreSQL browser on final patient-viewer-fixed source | 1/1 passed; downloaded FHIR R4 bundle validated | `test-reports/action-v1/final-pg-browser.json` |
| Earlier sequential fresh SQLite browser journeys alongside full regression | **10/10**, 0 failed/skipped/flaky, no test retries; one logged SQLite request error | `test-reports/release/action-v1-final-10/` |
| Final sequential fresh SQLite browser journeys after other suites finished | **10/10**, 0 failed/skipped/flaky, no test retries, no logged SQLite lock error | `test-reports/release/action-v1-release-10/` |
| Additional visual-capture journey | 1/1 passed | `test-reports/release/action-v1-visual/` |
| Existing replay smoke | **12/12**, 10344 ms, 0 live model-generation requests | `test-reports/action-v1/smoke.json` |
| Existing release-artifact redaction tests | 2/2 passed in each of 2 invocations | `test-reports/action-v1/release-tools.log`, `release-tools-final.log` |

The smoke used a private migrated SQLite database and the existing replay files, confirmed the default demo date and Amira IN_WINDOW, dating hold and both accepted Amira explanation replays, and made a read-only authenticated provider catalog request. It made no live explanation/investigation request. Main application databases and `.env` were not changed. PostgreSQL regression fixtures create/drop isolated test schemas. The combined runner passed 64 React tests before the final local viewer reset; the final full React suite passed 65 including its new regression. Backend hashes are identical to those used for the completed full SQLite/PostgreSQL suites. All 15 final application/test source hashes were frozen before the last PostgreSQL journey and isolated ten-run sequence and checked unchanged before release.

## Preserved failures and corrections

1. Initial targeted pytest invocation used the repository root instead of `backend`: **0 tests executed, 2 collection errors**, `ModuleNotFoundError: No module named app`. Correct-directory rerun: 38 passed. Evidence: `test-reports/action-v1/stage1-collection-failure.txt` and the original Codex tool output.
2. Initial stage-3 journey: **0/1 passed**. New loading text used `role="status"`, making the existing exact closure-confirmation role selector ambiguous. Loading text now uses a polite live announcement; the existing assertion was preserved. Redacted JSON, context and complete trace: `test-reports/release/action-v1-stage3/`.
3. First attempted ten-run batch: **0/1 completed journeys passed**, then the next run was deliberately interrupted. The new exact-text assertion could not select action text that shared its enclosing element with explanatory prose; its failure snapshot showed the correct completed state and “None” action. The action now has a separate span, and the exact assertion is unchanged. Complete failed-run JSON, context and trace remain in `test-reports/release/action-v1-consecutive-10/`. The interrupted second run is excluded from counts. One unfinalized invalid ZIP from that interrupted run was discarded after recording its size/hash/reason; valid archives and raw trace fragments were retained/redacted. See `interrupted-run-preservation.json`.
4. First combined full-regression wrapper was interrupted by a relative Tee-Object log path after the existing script changed working directory. Its SQLite JUnit summary reports **75 tests, 1 internal I/O error, 0 assertion failures**; its incomplete XML contains 76 testcase elements (74 named passing tests, one unnamed in-progress element and the pytest internal-error element). This was not a completed suite and is not counted as passing. Its empty summary and original XML remain in `test-reports/20261121-075908-82f28b98/`. The wrapper was rerun with an absolute log path; final full suites passed. No application/test assertion was changed for this tooling failure.
5. Transient **SQLite “database is locked” at BEGIN IMMEDIATE** was logged in the first earlier ten-run journey's coordination-queue request and the separate visual-capture journey's clock request, while verification jobs were running concurrently. Both journeys passed their assertions. These request errors remain in the original logs; their root cause is not claimed resolved or proven pre-existing. Because of this observation, the final source (with only the local viewer-state reset since the earlier sequence; unchanged backend and request patterns) was tested in a further ten consecutive journeys after other suites finished: **10/10 passed with no logged SQLite lock error**. React Query retains its existing request-retry behavior; Playwright test retries were not added. No assertion was weakened and no database timeout/transaction policy was changed. Concurrent verification load remains a known reliability limitation, not a clean-error-log claim for the earlier runs.
6. A review-added patient-switch regression reproduced stale local source-viewer content after another patient's trace loaded: **64 passed, 1 failed** in the full React invocation. Reproduction log and XML remain at `test-reports/action-v1/viewer-isolation-reproduction.*`. The viewer is now keyed by patient so its local opened-source state is discarded on patient change. The identical assertion then passed in the final **65/65** React run. Backend authorization and APIs were unchanged.

## Test assertion changes

Existing React assertions: **none changed**. New tests cover all eight known statuses plus unknown, data-driven action replacement/version binding, unchanged calculator/owner state, policy-derived trace contents and source links, patient-switch source-viewer isolation, patient grants, role/demo/confirmation guards, durable source versions/audits, reclosure blocking and visible lifecycle/error behavior.

The browser extension replaces only the old direct “Invalidate TSP result” click with the confirmed Evidence & audit control. The existing completed-window, approval-alone-open, closed-window, reopened IN_WINDOW and reopened-obligation assertions remain. Added exact assertions cover IN_WINDOW → “Send to reviewer (Coordinator)”, DUE_SOON → “Schedule assessment (Coordinator)”, completed → no action, correction response and visible confirmation, unchanged owner, closure_reopened audit, lifecycle reopening, pending-confirmation policy/version/eligibility and authenticated source viewer. No waits, timeouts, retries or earlier assertions were weakened.

## Files changed

- `backend/app/prevention/coordination.py`
- `backend/app/prevention/coordination_policy_v1.json`
- `backend/app/prevention/demo_corrections.py`
- `backend/app/prevention/tsp_api.py`
- `backend/tests/test_coordination.py`
- `backend/tests/test_demo_corrections.py`
- `frontend/e2e/journey.spec.ts`
- `frontend/src/Coordination.test.tsx`
- `frontend/src/Coordination.tsx`
- `frontend/src/DemoCorrection.test.tsx`
- `frontend/src/DemoCorrection.tsx`
- `frontend/src/Jury.tsx`
- `frontend/src/screens.tsx`
- `frontend/src/showcase.tsx`
- `frontend/src/style.css`
- `docs/ACTION_V1_REPORT.md` (this report).

Existing browser-test dashboard PNG side effects are preserved privately under `test-reports/action-v1/legacy-dashboard-test-output/` and restored to the baseline before release; they are not product changes. Actual correction/reopening mobile captures were visually inspected under `test-reports/action-v1/visual/`.

## Limits

- Coordination instructions are reminders, not executed actions, clinical advice or changes to obligation ownership. Completion status is distinct from verified clinical closure.
- No approved source guideline is supplied; the placeholder stays “pending clinical confirmation”. Existing synthetic timing/eligibility and history rules are unaltered.
- The demo correction control targets recorded synthetic workflow closing Observations; it is not a general external-facility correction editor. Other source-authority paths remain as before.
- No live model-generation reliability evaluation was requested or performed in this task. Replay grounding was exercised unchanged. The optional concurrent-capture SQLite contention observation remains visible above.
- This branch excludes the unmerged plum restyle by explicit user instruction. Long evidence/source views retain their existing scrolling behavior.
