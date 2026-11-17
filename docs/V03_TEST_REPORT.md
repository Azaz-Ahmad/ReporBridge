# ReproBridge v0.3 test report

The baseline at `d97b4cf` passed 36 Python tests on each database, three React tests, the production build, and two PostgreSQL browser journeys. The full v0.3 run is recorded in `test-reports/20261117-224751-7d95bc0a`.

| Suite | Verified result |
| --- | --- |
| Python unit and PostgreSQL integration | 38 passed, including 8 unit and 30 integration cases |
| Python unit and SQLite integration | 38 passed, including the same 8 unit and 30 integration cases |
| React components and readouts | 7 passed |
| TypeScript and Vite production build | Passed |
| PostgreSQL Playwright journey and replay | 2 passed in independent migrated schemas |
| Downloaded FHIR R4 bundles | Both full-run bundles and the screenshot replay bundle passed the official schema and patient-local reference checks |
| Screenshot replay | 1 additional PostgreSQL journey passed using the final evaluation readout and screenshot layout |
| Labeled synthetic rule decisions | 4 of 4 matched the expected detection or abstention result |
| Live PostgreSQL upgrade and API restart | Snapshot preserved and frontend proxy reported ready. Amira remained at preconception. |

The backend cases retain the v0.2 safety suite and cover fixture authorization, no-op replay, unrelated patient preservation, archival of closure and blocked attempts, and refusal when nonfixture evidence is present. The browser runs exercise actual node traces, dependency drill-down, missing-evidence and missing-approval blocks, review role switches, verified closure, FHIR download, responsive views, and the reset and archive summary. The initial v0.3 browser checks exposed ambiguous selectors after navigation. Distinct labels and updated selectors resolved the issue before the successful replay.

From the repository root, run `& .\scripts\Test-Demo.ps1 -PostgreSQL`. Publish the in-app technical evidence using `.\.venv\Scripts\python.exe scripts\publish_evaluation.py <completed-report-directory>`. The published figures describe test and synthetic scenario results. They establish no clinical outcomes.

For the screenshot replay, set `E2E_BROWSER_CHANNEL` to `msedge` and `REPROBRIDGE_CAPTURE_DIR` to the absolute path of `docs/screenshots/v03`, then run `.\.venv\Scripts\python.exe scripts\verify_postgres.py browser test-reports\v03-screenshot-replay\browser.json`.
