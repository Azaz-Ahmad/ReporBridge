# ReproBridge v0.5 Sprint 1 test report

Baseline `6a3dfb7` passed 39 checks on each database, nine React tests, the build and two PostgreSQL journeys. The final Sprint 1 run is `test-reports/20261118-002726-756e5c55`.

| Suite | Verified result |
| --- | --- |
| Python with PostgreSQL | 53 passed, including 14 M08 cases |
| Python with SQLite | 53 passed |
| React | 9 passed |
| TypeScript and Vite production build | Passed |
| Playwright on PostgreSQL | 2 complete Amira journeys passed in isolated schemas |
| Downloaded FHIR R4 bundles | Both passed independent bundled-schema and patient-local reference checks |
| Live migration | PostgreSQL backed up and upgraded to 0004. The original workflow snapshot matched before and after. |
| Live clinical explorer | 16 source events loaded, scoped document search returned both matching sections, existing workflow FHIR export returned HTTP 200. Edge capture was inspected and the expanded panel fit at 390 px. |

M08 cases cover typed filters, pagination, invalid FHIR, denied scope and direct IDs, nested references, exact identity and ambiguity, document format and metadata checks, source excerpts, duplicates, concurrent retries, invalid data rollback, version lineage, timestamp order, unresolved units, hybrid retrieval, freshness policy, all seven tools and workflow reopening. Browser assertions cover blocked and verified closure, archived reset, new evidence search and responsive layout. The explorer’s initial browser test matched a repeated label across results. The assertion was scoped to the actual opened document, then both clean replays passed.

Run `& .\scripts\Test-Demo.ps1 -PostgreSQL` from the repository root. The reviewed live capture is `docs/screenshots/v05-s1/clinical-explorer.png`. Test credentials and database contents stay in local ignored paths.
