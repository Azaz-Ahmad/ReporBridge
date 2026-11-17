# Test report

Executed on Windows with Python 3.12.10, Node.js 26.5.0, npm 11.17.0, Docker Desktop, PostgreSQL 17, and Microsoft Edge.

| Verification | Result |
| --- | --- |
| Alembic upgrade | Applied on the live PostgreSQL database and on isolated test databases |
| SQLite API integration | 12 passed |
| PostgreSQL API integration | 12 passed using isolated schemas |
| React component tests | 3 passed |
| TypeScript and Vite production build | Passed |
| Playwright browser journey | 1 passed in Edge against real FastAPI and migrated SQLite |
| Live PostgreSQL health and Vite proxy | API ready, database PostgreSQL, frontend HTTP 200, proxied API ready |
| Dashboard rendering | Edge desktop and mobile viewport checks passed without browser errors or horizontal page overflow |
| API process restart | Seeded obligation ID and all three initial audit events persisted |

| Feature | Classification | Verification |
| --- | --- | --- |
| Synthetic import, deterministic triggers and obligation passport | COMPLETE | Imports and rule output tested, including missing, conflicting, and nonfinal trigger evidence |
| Life-stage transition and dependency | COMPLETE | Preconception obligation retained, concurrent registration idempotent, edge traceable, linked open predecessor blocks closure |
| LangGraph coordination | COMPLETE | Runs using scoped evidence, reports missing or conflicting evidence, and persists a human review task |
| Role-based review and evidence-verified closure | COMPLETE | Approval, reject, request evidence, stale evidence, forbidden roles, missing and contradictory completion, and successful closure tested |
| Audit trail and restart persistence | COMPLETE | Successful and blocked attempts retained, seeded history verified after the live API restart |
| Bounded FHIR import and export | COMPLETE | Round-tripped the seven supported import types, rejected malformed resources, and validated exported Bundle, Task and Provenance against the official R4 schema |
| Five React screens | COMPLETE | Browser journey used all five routes, both acting roles, blocked and verified closure, FHIR download, and refresh |
| Full FHIR profiles and terminology, production identity and audit controls | NOT STARTED | Future integration and production work |
| Mother–child continuity and live institutional adapters | NOT STARTED | Architectural extension and roadmap |

The live database was left with the initial preconception fixture for a fresh walk-through. The automated journey ran separately. The two configured rules are illustrative and have no clinical approval.
