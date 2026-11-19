# TSP v1 — HealthX synthetic demonstration

**Release: GO for the local synthetic HealthX demonstration only.** All mandatory regression gates passed. Not clinically validated; policy defaults and citation remain pending clinical confirmation. Branch `feat/tsp-window`; release tag `tsp-v1` (annotated).

## Implemented
Seven staged commits add policy/calculation, versioned dating, scoped APIs/session clock, responsive UI, read-only agent context, completion classification, and deterministic fixtures/reset/journey. No dependency was added. Existing source grounding, closure gates, patient authorization, six-node investigation and seven M08 tools remain intact. The synthetic terminology list recognizes two additional dating codes.

- Policy/data/calculation: `backend/app/prevention/{tsp_policy_v1.json,window.py,timing.py}`.
- Projection/clock/routes/fixtures/guard: `backend/app/prevention/{tsp.py,tsp_schema.py,tsp_api.py,tsp_demo.py,window_grounding.py}`.
- Additive migrations: `0007_tsp_policy.py`, `0008_tsp_demo_clock.py`; migration metadata and health head updated.
- Investigation context/packet/checks: `backend/app/investigation/{service.py,graph.py,contracts.py,grounding.py}`. Window results are server-owned; models cannot write them. TSP explanations must copy the exact policy-cited server rendering; altered policy/date/status output is rejected. Source checks remain additive and unchanged.
- Exact recorded fixture completion is recognized by `backend/app/demo.py` for archival reset; other imported evidence still blocks reset.
- UI/tests: `frontend/src/{Tsp.tsx,Tsp.test.tsx,App.tsx,screens.tsx,style.css}`, `frontend/{playwright.config.ts,e2e/journey.spec.ts}`, `backend/tests/test_tsp.py`.
- Configuration/reset: `.env.example`, `scripts/Reset-TspDemo.ps1`. No secrets are committed.

## Verification invocations
Counts below are individual invocations, not additive unique coverage. Saved XML/JSON is under ignored `test-reports/`.

| Invocation | Actual outcome |
|---|---|
| Stage 1 first command, wrong import root | 0 passed; 1 collection error (`ModuleNotFoundError: app`) |
| Stage 1 corrected backend command | 11 passed |
| Stage 2 first edit command, incorrect relative path | Edit failed; unchanged 11 tests passed; no commit |
| Stage 2 corrected command | 15 passed |
| Stage 3 first edit command | UTF-8 decoding failure before wiring; tests not run |
| Stage 3 initial tests (`tsp-stage3.xml`) | 15 passed; 1 setup error (Windows shared pytest temp access denied) |
| Stage 3 local-temp retry (`tsp-stage3-retry.xml`) | 16 passed |
| Stage 3 prevention/workflow regression | 48 passed |
| Stage 4 initial edit command | Wrong CSS filename; tests/build not run |
| Stage 4 corrected build + React | Build passed; 27 tests passed |
| Stage 5 TSP + investigation | 58 passed; scripted providers, no live LLM |
| Stage 6 TSP + workflow | 51 passed |
| Stage 7 TSP fixture tests | 21 passed |
| Stage 7 build + React | Build passed; 27 tests passed |
| Initial full SQLite (`tsp-full-sqlite.xml`) | 203 passed |
| Initial full PostgreSQL (`tsp-full-postgres.xml`) | 203 passed |
| Stage 7 PostgreSQL browser (`tsp-stage7-browser.json`) | 1 failed: locator matched overall and W1 completion badges |
| Scoped-locator retry (`tsp-stage7-browser-retry.json`) | 1 passed; exported FHIR structure/references passed |
| Final review (`tsp-review.xml`) | 24 passed |
| Final review with altered policy/date/status checks (`tsp-review-final.xml`) | 27 passed |
| Provenance build + React (`tsp-final-components.xml`) | Build passed; 27 tests passed |
| Release build + React (`tsp-release-components.xml`) | Build passed; 27 tests passed |
| Release SQLite (`tsp-release-sqlite.xml`) | 209 passed: original 182 plus 27 TSP tests |
| Release PostgreSQL (`tsp-release-postgres.xml`) | 209 passed: original 182 plus 27 TSP tests |
| Release PostgreSQL browser (`tsp-release-browser.json`) | 1 passed; exported FHIR structure/references passed |

Failures are retained above and in the original failed XML/browser report; successful retries use different filenames. Earlier source-edit failures are recorded here and in the Codex transcript. No real LLM requests were made for this task; window integration uses the existing test-double provider. Existing unrelated live-evaluation records are not presented as TSP verification.

## Local deployment
The public PostgreSQL schema was backed up to ignored `test-reports/tsp-pre-migration-public.dump`. Migrations advanced 0006 to 0008. Hash/count checks confirmed all pre-existing contents of all 27 tables were unchanged by migration (excluding the one newly added policy row). See `tsp-migration-verification.json`.

The local backend was restarted, ignored `.env` DEMO_MODE enabled, and the authorized TSP reset/seed run. Smoke evidence: `tsp-runtime-smoke.json`: PostgreSQL ready; Amira IN_WINDOW; uncertain patient HOLD_DATING_UNCERTAIN; demo date 2026-11-22. No LLM calls. Prior Amira workflow history is archived by the existing reset mechanism; independent M08 feed and unrelated patients are preserved.

One-command reset (executed successfully): `powershell -File scripts/Reset-TspDemo.ps1` (backend default port 8000). UI **Reset TSP demo** also restores the calling browser's demo date. Clocks are session-local, not global; the script gets its own session. Load/seed does not shift an existing pregnancy when the clock advances.

## Defaults requiring clinical confirmation
All policy values retain `CITATION_PENDING_CLINICAL_CONFIRMATION` and the visible label **pending clinical confirmation**:
- W1: pregnancy registration through GA 104 inclusive, only for a carried unresolved preconception obligation.
- W2: GA 168–202 inclusive.
- Due soon: seven calendar days before a window opens; in-window endpoints remain IN_WINDOW.
- Dating conflict: difference strictly greater than seven days holds; seven days is allowed.
- Dating arithmetic assumes a 280-day LMP-to-EDD/EDD-to-GA origin. Within tolerance the earliest supported EDD is selected, with every source disclosed; this is not clinical source precedence.
- Earliest qualifying dated reconciliation evidence on/after each window start determines in-window versus late. Existing reviewer/source/dependency closure requirements still apply.
Clinical teammates must confirm the above arithmetic/selection/interpretation, intended prerequisite/pathway mapping and authoritative citation before clinical use.

## Known limits
Synthetic demo only, one pathway. No diagnosis, glucose-value interpretation or new clinical thresholds. Clinical policy/citation is unconfirmed. Ordinary assessment presence does not bypass the existing reconciliation evidence or closure gates. The seeded synthetic result is historical (seed anchor minus seven days) and carries no glucose value. Existing M08 rejection/quality warnings for future-dated records remain active; the demo clock changes projection dates only. Current source evidence is reprojected, not a historical reconstruction of what was known on an earlier clock date. TSP model explanation is integrated with the existing single-agent investigation and mandatory review; it has not been live-provider evaluated. Broader multi-agent workflows and clinical integrations retain their existing scope. Reset archives/restarts Amira and refreshes dating fixtures; independent evidence and unrelated patients are preserved.

Final full-suite durations: SQLite 268.12 s; PostgreSQL 505.17 s. Final browser duration 79.73 s, one pass, no skips/flakes. These are test-run durations, not application latency guarantees. Final aggregate evidence: `test-reports/tsp-release-summary.json`. No remote push or history rewriting performed.
