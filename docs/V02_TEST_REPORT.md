# Ajyra AI - ReproBridge v0.2 test report

Verification ran on Windows with Python 3.12.10, Node.js 26.5.0, Microsoft Edge, and a local Docker PostgreSQL 17 instance. The baseline was `bdd195c`. The earlier [baseline audit](V02_BASELINE_AUDIT.md) records the original passing suite and independent defect reproductions.

| Suite | Result |
| --- | --- |
| Python rule and reconciliation unit tests | 8 passed per database-suite invocation |
| PostgreSQL integration | 28 passed on fresh migrated schemas, including an upgrade from revision 0001 |
| SQLite integration | 28 passed as supplementary coverage |
| React components | 3 passed |
| TypeScript and Vite production build | Passed |
| PostgreSQL Playwright journey and clean replay | 2 passed, one complete journey per fresh schema |
| Downloaded FHIR bundles | Both passed R4 structural and local-reference checks |
| Actual PostgreSQL and API restart | Persisted snapshot matched before and after both restarts. A replayed pregnancy event changed neither the snapshot nor audit. |
| Live v0.2 upgrade | Created a PostgreSQL backup, applied the migration, and verified the API version, database health, frontend and proxy. The original obligation and all three original audit events were present. Amira remained at preconception. |

Run `& .\scripts\Test-Demo.ps1 -PostgreSQL` from the repository root. The full Pytest total is 36 for each database configuration. The final run is in `test-reports/20261117-221832-ba1cfdba`. The report directory contains JUnit, Playwright JSON, a suite summary, and each downloaded and validated bundle. The test script asserts a clean browser pass for each of two separate schemas. Run `.\.venv\Scripts\python.exe scripts\verify_postgres.py restart test-reports\v02-restart.json` for restart and timing checks on the local Compose database.

Coverage includes rule abstention, version drift, typed dependency and cycle guards, concurrent registration, role and cross-patient evidence enforcement, graph execution, failure and retry, stale or unrelated approvals, rejected decisions, invalidated completion evidence, cascading reopening, audit and closure history, FHIR imports and export, and browser role switches and patient selection. The graph failure and interruption paths use injected errors. Successful runs invoke the actual deterministic LangGraph workflow.

## Measured local behavior

The restart run used the actual HTTP API with a warm connection and a small isolated PostgreSQL schema.

| Operation | Samples | Median | Max |
| --- | ---: | ---: | ---: |
| Repeated clinical evaluation | 8 | 8.15 ms | 9.64 ms |
| Snapshot read | 8 | 12.48 ms | 17.73 ms |
| First pregnancy registration | 1 | 38.79 ms | 38.79 ms |
| Fresh LangGraph execution and persistence | 2 | 20.90 ms | 23.20 ms |

PostgreSQL restart to API readiness took 1.374 s. API process start to readiness took 3.785 s. The patient-evidence query used a sequential scan of a two-row fixture and reported 0.013 ms execution. The final browser pair measured 1.215 s and 1.442 s for page load, token sign-in and dashboard readiness, then 179 ms and 104 ms for workspace navigation. These are local measurements on a tiny dataset.
