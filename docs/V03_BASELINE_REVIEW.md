# Ajyra AI - ReproBridge v0.3 baseline review

The checkout at `F:\ReproBridge` started clean at `d97b4cf`. The product scope, architecture, demo script, v0.2 test report and defect register, known limitations, five React routes, API handlers, database schema and agent pipeline were inspected before changes.

| Screen | Observed baseline |
| --- | --- |
| Population | Five metrics read the persisted snapshot. The registry links to patient records. There is no blocked count, dedicated Amira entry point, or in-app evaluation. |
| Workspace | The patient selector, timeline, evidence and pregnancy action are API-backed. The timeline has no compact current-stage journey or linked dependency visualization. |
| Passport | Source, rule version, owner, follow-up, dependencies and audit appear as fields and links. It has no lifecycle summary or expandable provenance. |
| Resolution | Real LangGraph retrieves supplied authorized records, reconciles, prepares and routes. The snapshot includes run outcomes, evidence references, proposals and decisions. It has no persisted per-node trace. |
| Evidence and audit | The coordinator can submit fixtures, and persisted audit shows blocked, reopened and verified closures. The patient bundle downloads through the FHIR R4 endpoint. Validation is structural with patient-local references. |

Coordinator, reviewer and viewer tokens are enforced by the backend. Mutations invalidate the TanStack Query snapshot. The supported clinical transition is preconception to pregnancy. PostgreSQL stores the typed edges. There is no external LLM, outbound dispatch or live EMR connection. Mother–child continuity is planned.

Baseline command `& .\scripts\Test-Demo.ps1 -PostgreSQL` ran 36 tests per database, three React tests, the production build and the browser journey and replay. All suites passed, including both PostgreSQL browser runs and their local FHIR checks. Run artifacts are in `test-reports/20261117-223051-8de5b15f`.
