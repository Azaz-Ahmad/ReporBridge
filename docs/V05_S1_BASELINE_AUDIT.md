# Clinical data foundation baseline

The clean checkout at `F:\ReproBridge` started at `6a3dfb7`, with Alembic head `0003`. The audit inspected the persisted fixture, patient and evidence tables, closure storage, role tokens, authorization checks, FHIR import and bundle export, archive/reset, change audit, and the four-node deterministic LangGraph workflow.

Reuse the bundled R4 structural schema, literal patient-local reference validation, synthetic tags, immutable workflow evidence, coordinated database transactions and closure reopening. The baseline had no patient grants, external identity claims, clinical document index or versioned event ledger.

Baseline `test-reports/20261118-000510-55d6693a` passed 39 Python tests on each database, nine React tests, the production build and two PostgreSQL browser journeys with independent FHIR validation.
