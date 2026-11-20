# Ajyra AI - ReproBridge v0.4 baseline review

The checkout at `F:\ReproBridge` was clean at `7e51eec` before changes. The review inspected the five React routes, Amira’s seed, rule definitions and provenance, graph nodes and execution payload, dependency and closure logic, archive/reset implementation, and test suites.

| Area | Observed baseline |
| --- | --- |
| Population | Persisted metrics and a direct link to Amira. The product summary was generic. |
| Patient workspace | API-backed timeline, pregnancy registration, and a dependency graph. The source was a generic synthetic follow-up flag. |
| Passport | Rule, ownership, evidence, dependencies and closure controls were present. Technical identifiers occupied the main view and the current blocker required a closure attempt to inspect. |
| Care resolution | Four actual nodes ran locally and persisted a successful trace. Before execution, the screen provided a short empty-state message. Authorization, audit and human review are outside the compiled graph. |
| Evidence and audit | Structural FHIR R4 export, local reference checks, lifecycle history and evidence-specific closure were implemented. The audit recorded blocked reasons. |

The rules are deterministic and illustrative. The pregnancy review’s typed edge narrows verified closure of that review, rather than gating pregnancy care. Coordinator-only reset checks exact fixture data, archives prior records transactionally and preserves unrelated imports.

Baseline command `& .\scripts\Test-Demo.ps1 -PostgreSQL` produced `test-reports/20261117-232503-45244d9e`. The initial checks passed 38 Python tests on each database, seven React tests, the production build and both PostgreSQL browser journeys and their FHIR checks.
