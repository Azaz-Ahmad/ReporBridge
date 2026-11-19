# Increment 2 release verification

Full release matrix: scripts/Test-Demo.ps1 -PostgreSQL, test-reports/20261119-231221-5b0cc6bf. Every exit code is zero.

| Gate | Observed result |
|---|---|
| Python / PostgreSQL | 144 passed |
| Python / supplementary SQLite | 144 passed |
| React components | 20 passed |
| TypeScript / Vite production build | Passed |
| Fresh PostgreSQL browser journey | Passed, 58.3 seconds |
| Independent PostgreSQL browser replay | Passed, 43.5 seconds |
| Downloaded FHIR exports | Both passed bundled R4 structure and patient-local reference validation |

All 110 Increment 1 Python tests and all 16 Increment 1 React tests remain. The 34 added backend checks exercise the 20 required scenario categories plus exact structured values, chronology, prerequisite integrity, retrieval caching, mode-safe replay, missing-provider behavior, partial approval, stale timing policy, the actual Responses specialist wire contract, exact-source serialization repair, withholding unsupported metadata and rejecting invented deadlines in clinician questions. Four new component tests verify attestation, trusted decision binding, actual failed/skipped states, partial packet handling and reviewer restrictions.

The existing browser journey retains all five screens, pregnancy transition, dependency graph, source explorer, decision recording/follow-up, clinical approvals/closure, archive/reset and export. It now also checks the multi-agent panel and its disabled execution when the provider is disabled. Browser regression tests do not make paid model requests.

After a final cleanup made the shared clinical envelope explicit in LangGraph state, all 34 affected checks were rerun on SQLite in test-reports/multi-eval-20261119-231724-44ba03 and PostgreSQL in test-reports/i2-final-handoff-postgres.xml. The matched synthetic scenarios use explicitly labeled doubles; none is an application fallback. The synthetic artifact includes 23 labeled scenarios and three matched comparisons; administrative/access-only assertions are represented in the JUnit output rather than invented model packets.

Real model verification is separate: all three required multi-agent cases passed in test-reports/multi-live-20261119-230124-e75d21, alongside three matched single-agent runs. A full-dataset actual run remains in the app, reviewed with request_evidence. Final authoritative-source revalidation is recorded in test-reports/i2-final-source-revalidation.json. All three matched live outputs also passed the expanded narrative/question safety filter.

Nine real screenshots under docs/screenshots/v06-i2 cover initial state, actual in-flight execution, reconciliation, context, gaps, unified packet, actual synthetic human review, linked decision and mobile. All were inspected; chronology source-label separation and stretched card heights were corrected. The expanded view passed the 390-pixel horizontal-fit check.

No critical authorization, evidence-integrity, clinical-decision or closure failure remains in the exercised cases. CONDITIONAL GO applies to this local synthetic capability, with the limitations and mixed performance results documented separately.
