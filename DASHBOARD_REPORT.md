# Jury dashboard v1

**GO for the synthetic demo dashboard.** Branch `feat/jury-dashboard`, based on passing `handoff-v1`. Annotated tag `dashboard-v1`.

## Changes
- `backend/app/jury.py`, `main.py`: default idempotent three-patient cohort (Amira Haddad, Lina Omar, Sara Ali), with existing pregnancy/obligation/event APIs and unchanged TSP policy/calculator. Explicit `REPROBRIDGE_TEST_MODE=true` retains diagnostic fixture creation and the legacy single-patient seed for tests. No migration/dependency or clinical-rule change.
- `frontend/src/Jury.tsx`, `screens.tsx`, `App.tsx`, `style.css`: first KPI Time-sensitive (backend WINDOW_PASSED + DUE_SOON); urgency-sorted queue, backend window ends, owner, facility and next action; one-line hero/one journey button; demo-only collapsed Admin drawer; plain activity with IDs/versions in tooltips and explicitly labeled demo-calendar dates; workspace pregnancy-week/window strip; larger/high-contrast presentation.
- Role switch uses the existing selected role's token and verifies its role through the existing session API. It never reveals/fetches another role's token or bypasses patient grants. Tokens are password inputs and are cleared after successful switching.
- Tests: `backend/tests/test_jury.py`, explicit test mode in `test_workflow.py` and `frontend/playwright.config.ts`; `frontend/src/Jury.test.tsx`, extended `frontend/e2e/journey.spec.ts`.
- Playwright captures: `demo-assets/dashboard-1366x768.png`, `dashboard-1920x1080.png`.

## Verification (each invocation, not cumulative coverage)
| Artifact / command | Actual result |
|---|---|
| dashboard-stage1.xml | 28 passed |
| Initial frontend build / dashboard-components.xml | Build passed / 34 passed |
| dashboard-browser.json | 1 failed: legacy registry assertions now inside collapsed Admin |
| Second frontend build / dashboard-components-final.xml | Build passed / 37 passed |
| dashboard-browser-retry.json | 1 passed; initial captures visually caught before queue loaded |
| Fixture-gate edit attempt / dashboard-fixture-gate.xml | Relative-path edit failed; unchanged one-test invocation passed |
| dashboard-fixture-gate-retry.xml | 9 passed after corrected gate implementation |
| Initial full dashboard-sqlite.xml | 218 passed |
| Initial full dashboard-postgres.xml | 218 passed |
| Third build / dashboard-release-components.xml | Build passed / 37 passed |
| dashboard-browser-final.json | 1 passed; captures wait for three names and fonts |
| Fourth build / dashboard-projector-components.xml | Build passed / 37 passed |
| dashboard-browser-role-switch.json | 1 failed: label selector did not resolve observed Demo role combobox |
| Fifth build / dashboard-layout-components.xml | Build passed / 37 passed |
| Final dashboard-release-sqlite.xml | 218 passed |
| Final dashboard-release-postgres.xml | 218 passed |
| dashboard-browser-release.json | 1 passed, including Coordinator → Reviewer → Coordinator |

All original 217 backend tests and 33 React tests are retained. Failed reports retain distinct filenames. Browser coverage retains legacy/TSP/handoff gates and adds the jury cohort, screenshots and positive role switching. No live LLM calls. The first local smoke request raced server startup (connection refused); health-ready retry succeeded: three expected backend statuses, diagnostic fixture gate 403, saved in `test-reports/dashboard-runtime.json`.

## Semantics and limits
Existing source history is preserved: old diagnostic patients are not deleted from an existing database; the default jury cohort is three plain-named patients, while historical/diagnostic records remain available administratively. A fresh default seed creates exactly three patients. Reset and diagnostic tools live in Admin; diagnostic creation requires explicit test mode. Facility absence is shown as “Facility not recorded,” never inferred. Reviewers still see only granted patients. Activity dates are a labeled demo-calendar projection; original audit timestamps remain unchanged. Week labels are display arithmetic from dating inputs; all window/status/closure/eligibility authority stays with existing backend services and human review. No empirical five-second usability study is claimed. Existing clinical-policy/citation limitations remain in force. No merge, push, force-push or history rewriting.

Final SQLite duration 245.45 s; PostgreSQL 671.88 s. All final suites have zero failures/errors/skips; browser zero flakes. Both final PNGs were visually inspected. At 1366×768 the urgent rows are prioritized above the fold and the queue continues vertically; 1920×1080 shows all three. Aggregate evidence: `test-reports/dashboard-release-summary.json`. Screenshots were captured after all three names and fonts loaded. Source and medical-history records were not deleted to clean the default presentation.
