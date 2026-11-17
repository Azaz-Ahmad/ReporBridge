# ReproBridge v0.4 test report

Baseline `7e51eec` passed 38 Python checks on each database, seven React checks, the production build and both PostgreSQL browser journeys. The full v0.4 run is in `test-reports/20261117-233652-4700179e`.

| Suite | Verified v0.4 result |
| --- | --- |
| Python unit and PostgreSQL integration | 39 passed, including 8 unit and 31 integration checks |
| Python unit and SQLite integration | 39 passed |
| React tests | 9 passed |
| TypeScript and Vite production build | Passed |
| Playwright PostgreSQL journey and clean replay | 2 passed in separate migrated schemas |
| FHIR exports | Both clean replay bundles passed the official R4 schema and patient-local reference validation |
| Final screenshot replay | 1 additional PostgreSQL journey passed, with independent validation of its downloaded bundle |
| Live restart | v0.4 reported ready against PostgreSQL. Existing pregnancy-stage records were preserved. |

Focused PostgreSQL regression also passed six checks covering the fixture, blocked and verified closure, reset and FHIR export. The expanded suite verifies legacy seed compatibility, safe archival and reset, unchanged rule decision definitions and refusal of unrelated fixture data. The browser checks the initial configured workflow, persisted execution, dependency rationale, blocked reasons, reviewer reapproval, FHIR download, responsive routes and reset. An initial browser attempt exposed long select labels forcing overflow. The corrected layout passed the 390 px checks in both clean runs.

Run `& .\scripts\Test-Demo.ps1 -PostgreSQL` from the project root. Regenerate the in-app test readout with `.\.venv\Scripts\python.exe scripts\publish_evaluation.py <passing-report-directory>`. The screenshot replay uses the same PostgreSQL browser harness, with `REPROBRIDGE_CAPTURE_DIR` pointing to `docs/screenshots/v04` and `E2E_BROWSER_CHANNEL` set to `msedge`.
