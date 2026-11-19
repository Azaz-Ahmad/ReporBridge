# Increment 2.1 regression report

Full command scripts/Test-Demo.ps1 -PostgreSQL passed. Final artifacts: test-reports/20261120-000636-6426fc1a; every suite exit code is zero.

| Gate | Actual result |
|---|---|
| PostgreSQL Python | 182 passed |
| Supplementary SQLite Python | 182 passed |
| React components | 22 passed |
| TypeScript/Vite production build | Passed |
| Fresh PostgreSQL browser journey | Passed, 47.1 seconds |
| Independent PostgreSQL browser replay | Passed, 38.5 seconds |
| Downloaded FHIR bundles | Both passed bundled R4 structure and patient-local reference validation |

All 144 previous Python tests and 20 previous React tests remain. The existing 34 multi-agent behavior assertions explicitly exercise the preserved legacy profile because optimized routing intentionally skips previously unconditional specialists. No original safety assertion was removed or loosened. The new default optimized path adds 38 checks: selective routing, all ten required matched categories, source/context immutability, exact structured values/chronology/citations, source change invalidation, cache scope/aliasing, semantic-safe section omission, concurrency with deterministic merge, unknown/unauthorized questions, model/tool failures, duplicate requests, interruption handling, preflight call accounting and ambiguous identity rejection. All use actual persisted M08/decision services with explicitly labeled test doubles.

The matched deterministic artifact test-reports/i21-eval-20261120-001514-591f82 records ten baseline/optimized pairs starting from identical source fingerprints. Clinical/decision fixture tables are restored only inside disposable test databases between profiles; investigation traces remain separate. No fixture reset runs against the live application. Its 38 checks passed independently as well.

Two new React checks prove that execution summary values and skipped reasons come from persisted backend accounting, and that absent legacy timing measurements are labeled unavailable. Existing five-screen browser journeys retain pregnancy transition, passport, dependency graph, source retrieval, prevention lifecycle, human review, evidence-specific closure, audit, reset and FHIR export. Browser regressions do not invoke paid models.

Live verification is separate and real: 12 primary matched runs and four serial/parallel runs all passed. An additional full-M08 run remains in the app and supplied seven actual inspected screenshots. The expanded panel and summary fit at 390 pixels. A tool-reference line separation fix improved trace readability without changing workflows.

No critical authorization, evidence-integrity, clinical-decision or closure defect remains in the exercised cases. Safety gates and performance targets are reported separately.
