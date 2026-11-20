# Ajyra AI - ReproBridge v0.2 baseline audit

The audit started at `F:\ReproBridge` on 17 November 2026 with a clean Git worktree at `bdd195c`. The baseline review covered the README and all nine existing reports and design documents, the five React routes, FastAPI routes and authorization, SQLAlchemy and Alembic, LangGraph, the FHIR schema and mapping, Docker Compose, and the test runners.

The baseline evaluation ran SQLite and PostgreSQL API suites, React component tests, a production build, and the Edge journey. All five commands exited zero. The browser harness used its own SQLite database. The live Docker PostgreSQL service reported healthy. Baseline artifacts are under `test-reports/20261117-220228-e777f0c5` in the local checkout.

| Screen | Baseline status | Observation |
| --- | --- | --- |
| Population intelligence | COMPLETE | Counts come from the API-backed snapshot. The Edge suite seeded and selected Amira. |
| Women’s health workspace | COMPLETE | Demographics and source history load from the database. The existing API suite exercised concurrent registration and the Edge suite exercised the transition. |
| Clinical obligation passport | PARTIAL | Source and rule version were visible. Dependency type and integrity were implicit in creation code. |
| Agentic care resolution | PARTIAL | The graph executed and persisted review tasks. Failed executions lacked a retained trace, and a missing-evidence proposal could be used to authorize closure after evidence changed. |
| Evidence and audit | PARTIAL | The suite exercised blocked and verified closure. A late contradictory import left a completed obligation closed. The export accepted unresolved supporting references and returned generic JSON. |

Independent isolated replay reproduced an approval and closure returning HTTP 200 after evidence arrived on a missing-evidence proposal, a late contradictory import returning HTTP 200 with the obligation still closed, and an export containing a dangling Encounter reference. The export response declared `application/json`. These cases were absent from the green baseline suites.

The architecture contains the focused five innovations and a future mother–child extension. The two rules use synthetic markers. No model calls, external messaging, or live clinical integrations are configured.
