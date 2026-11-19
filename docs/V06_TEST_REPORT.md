# v0.6 test report

The complete command scripts\Test-Demo.ps1 -PostgreSQL passed. Final artifacts are in test-reports/20261119-213336-5f0bb821.

| Verification | Actual result |
|---|---|
| Python on PostgreSQL | 110 passed |
| Python on supplementary SQLite | 110 passed |
| React components | 16 passed |
| TypeScript/Vite production build | Passed |
| PostgreSQL browser journey | Passed |
| Independent PostgreSQL browser replay | Passed |
| Downloaded FHIR bundles | Both validated against bundled R4 structure and patient-local references |

All 93 baseline Python tests and 12 baseline React tests are retained. The 17 prevention-domain checks cover creation, registry applicability, scoped access, reviewer authorization, immutable outcomes, obligation/decision separation, missing/conflicting evidence, correction invalidation, timing boundaries, no policy, retired/superseded policy, separate timing fixtures, reset preservation, concurrent outcomes, actual M08 adapters, trusted decision binding, replay and rejection of invented timing advice.

Four React tests cover backend queue counts, reviewer snapshot attestation/record submission, persisted timeline context and selected-decision links. The browser journey traverses all five screens, retains the full original clinical approval/closure path and adds decision recording, follow-up history, reset isolation and real backend timing counts. Paid model calls are disabled in browser regression tests.

## Genuine agent verification

The live app retained a real Gemini readiness run, investigation-4be08f8029e44cc5a211917843e365ff. It completed six actual model calls and five authorized M08 tool executions, validated conflicting_evidence and abstained, then entered pending_review.

Provider usage was 35,316 input and 2,466 output tokens, with zero retries. Requested model google/gemini-3.8-flash-20260902 and reported model google/gemini-3.8-flash are stored with response IDs. The application clinical snapshot was identical before and after this run.

Proof is in test-reports/v06-live-ae36a7bdc0/summary.json. A previous actual attempt was rejected for unknown_citation and conflict_not_acknowledged; its safe abstention remains in test-reports/v06-live-50b687bb37/summary.json and in the app's investigation history.

## Upgrade and visual verification

A PostgreSQL backup preceded migration 0006. All 22 previous tables matched before/after row counts and content hashes. Upgrade proof and dump are in test-reports/v06-upgrade-502117512e.

All five actual application screenshots were captured under docs/screenshots/v06 and inspected. A transient empty timeline capture was corrected by waiting for loaded data and exposing proper loading feedback. Intrinsic select/citation widths in the expanded agent view were fixed, and all five screens passed a 390-pixel horizontal-fit check. The mobile passport was also captured.

An intermediate run found a component test query-option error and ambiguous/toggle-sensitive browser locators after additive panels were introduced. Those test issues were corrected. The final two fresh browser journeys passed.

The release gate is GO for this local synthetic increment. Clinical sufficiency and any clinical timing policy still require appropriate human/clinical approval.
