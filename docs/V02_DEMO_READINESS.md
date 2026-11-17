# ReproBridge v0.2 demo readiness

**CONDITIONAL GO for the synthetic HealthX Ajyal walkthrough.** The mandatory prototype workflow and safety checks passed. Operate on loopback with the fabricated dataset and use the documented review sequence. Full FHIR validation, production identity and clinical approval remain outside this demonstration’s assurance.

| Gate | Result |
| --- | --- |
| Population dashboard | COMPLETE. API-derived counts, patient selection, browser reload, and current closure totals verified. |
| Women’s health workspace | COMPLETE. Demographics, source observation, persisted preconception and pregnancy events, and stage replay verified. |
| Clinical obligation passport | COMPLETE. Stable source and version, owner, preserved history, typed dependency, and current closure state verified. |
| Agentic care-resolution center | COMPLETE. Actual evidence-dependent LangGraph runs, approval and rejection boundaries, failed execution audit, and successful retry verified. |
| Evidence and audit | COMPLETE. Missing, conflicting, unqualified and unauthorized closure attempts blocked. Verified closure, reopening, audit persistence and patient export verified. |
| Database and migration | PASS. PostgreSQL migration, independent browser replay, actual database and API restart, and transition replay verified. |
| FHIR | PASS at declared structural and patient-reference validation level. |
| Production frontend | PASS. Build and Edge journeys passed. |

Nine verified defect groups were fixed. The complete Amira journey and clean replay passed on independent PostgreSQL schemas. The demo first approves the coordination action, records a blocked attempt without completion evidence, then obtains a second approval against qualifying evidence and verifies closure. The two checked bundles are report artifacts.

Follow [the demo script](DEMO_SCRIPT.md). See [the test report](V02_TEST_REPORT.md), [defect register](V02_DEFECT_REGISTER.md), and [remaining risks](V02_REMAINING_RISKS.md).
