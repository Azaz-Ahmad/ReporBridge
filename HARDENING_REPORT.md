# Demo hardening implementation and verification

**Decision: NO GO for a demo promising accepted model-backed explanations.** The hardening implementation and final regressions passed; the real explanations safely abstained or were rejected. The smoke intentionally returns failure for unavailable/rejected explanations. No guard was relaxed to turn these outcomes into success.

Branch `feat/demo-hardening`, from latest passing `cb27467` (follow-up navigation fix). Staged commits: `8b8bdd4`, `ff27c36`, `687dbf0`, `0c815b4`, `d88ae16`, `3409e26`; this report commit receives annotated tag `hardening-v1`. No merge, push, history rewrite or previous-tag change.

## Implemented scope

1. Model and endpoint come from environment. `OPENAI_MODEL` is required; no model default/switch. Blank `OPENAI_BASE_URL` uses the official endpoint. Rejected models get a clear controlled configuration error; upstream bodies and credentials are not logged. Exact variables: `.env.example` and `docs/DEMO_HARDENING.md`.
2. Explicit `LLM_MODE=live|replay`; configurable `LLM_REPLAY_DIR`, optional deliberate `LLM_RECORD_DIR`. Same six-node graph and seven authorized M08 tools run in replay; actual current tools feed unchanged grounding. Context/source/version/digest/quality/policy/date changes fail closed. Equal-time page compatibility requires the original recorded request hash. Receipt transport metadata is normalized only for matching. Replay has zero live calls/tokens and separately records original token metadata. The small mode indicator is inside Admin only.
3. Actual synthetic live captures and measured results retained. `scripts/record_demo_llm.py` uses isolated migrated databases, zero retries, secret stripping, no overwrite and a tested setup-only path. Curated real abstention/failure captures are committed in `backend/demo-replays/hardening-v1/`; original attempts and failed offline checks remain locally preserved. Nothing is substituted with a mock. Test doubles are confined to regression evaluations.
4. Reset TSP requires a separate confirm/cancel step; Amira reset remains nested and explicitly confirmed. Synthetic timestamp wording is explanatory, with the original M08 flag/state retained. The journey verifies the advanced clock presentation and a fresh browser profile's default **2026-11-22** after reset. Pregnancy dates, age-16 history and clinical semantics are unchanged.
5. `scripts/smoke_demo.py` has a total 60-second budget, local-only role-token target, explicit pass/fail results, guarded reset, status checks, actual replay and a read-only live catalog probe. It sends no patient data to that probe and makes no generation request. Catalog reachability is separate from model permission/quality; actual live captures establish model acceptance. `RUNBOOK.md` is a 492-word start/reset/demo/failure guide.

No dependencies or migrations were added; existing head **0009** is checked by health and exercised in isolated test databases. The exact uncertain-dating fixture now receives canonical synthetic identity attestation; patient grants/authorization are unchanged and an ungranted viewer is denied. M08 contracts, patient authorization, grounding implementation, closure gates, deterministic window/history rules and their citation placeholder remain unchanged. The graph change concerns replay usage accounting only. Agents have no authority to change timing, eligibility, relevance or closure.

## Actual live investigations

Requested model read from the local environment: `google/gemini-3.8-flash-20260902`. Provider-reported alias: `google/gemini-3.8-flash`. Both identifiers are retained. No alternative model was selected. These are recording metadata, not application model defaults.

| Investigation | Latency ms | Reported input / output tokens | Model turns | Actual outcome (all abstained) |
|---|---:|---:|---:|---|
| TSP Amira initial | 22898 | 29599 / 1408 | 5 | tool_budget_exhausted |
| Historical Amira initial | 22570 | 19344 / 2817 | 3 | incomplete_response |
| Uncertain dating (only live run) | 60354 | 32384 / 3538 | 6 | incomplete_response |
| TSP Amira approved repeat | 32816 | 32598 / 1662 | 6 | tsp_window_or_policy_mismatch |
| Historical Amira approved repeat | 32756 | 41201 / 3074 | 5 | incomplete_response |

Five actual investigations: two initial required cases, one uncertain scenario capture, and the two explicitly user-approved repeats. There were **25 model turns**, no retries. Reported usage totals **155,126 input / 12,499 output tokens**; incomplete-response usage is flagged incomplete and is not presented as a definitive bill/cost. The repeat TSP final Draft parsed, then failed the original timing/policy guard. The other failures produced no accepted final explanation. No risk/window guard was weakened; no more paid calls were made.

All three curated captures were verified offline against fresh synthetic databases: same authorized tools, validation outcomes, errors, abstention and tool counts; zero live calls/tokens. Source IDs are rebound to current authorized handles, so fidelity comparison retains semantic validation and source counts rather than requiring old random IDs. The replay contains real failed outputs/terminal error metadata; it does not invent successful answers.

## Final regression and exact invocation ledger

Full backend: **254 passed SQLite**, **254 passed PostgreSQL**, no failures/errors/skips. React: **46 passed**. Final production build passed. Browser: **10 consecutive complete journeys passed**, no retries, failures, skips or flaky results. Each uses a fresh synthetic SQLite database and dedicated report/artifact directory. The journey retains the existing disabled-provider check; real replay integration is verified separately through the three captured cases, not falsely claimed as ten live model runs.

The final catalog-only script extension was additionally checked with the three targeted smoke regressions; no application/clinical code changed after the full-suite source freeze. Exact invocations below are separate runs, not cumulative unique-test counts.

| XML artifact under test-reports/ | Passed | Failed | Errors | Skips |
|---|---:|---:|---:|---:|
| hardening-final-focused.xml | 16 | 0 | 0 | 0 |
| hardening-full-components.xml | 46 | 0 | 0 | 0 |
| hardening-full-postgres.xml | 254 | 0 | 0 | 0 |
| hardening-full-sqlite.xml | 254 | 0 | 0 | 0 |
| hardening-smoke-details.xml | 3 | 0 | 0 | 0 |
| hardening-smoke-reachability.xml | 3 | 0 | 0 | 0 |
| hardening-stage1.xml | 43 | 0 | 0 | 0 |
| hardening-stage2-components.xml | 42 | 0 | 0 | 0 |
| hardening-stage2-final.xml | 67 | 0 | 0 | 0 |
| hardening-stage2-status.xml | 7 | 0 | 0 | 0 |
| hardening-stage2.xml | 67 | 0 | 0 | 0 |
| hardening-stage3-final.xml | 10 | 0 | 0 | 0 |
| hardening-stage3-setup.xml | 10 | 0 | 0 | 0 |
| hardening-stage3-transport.xml | 11 | 0 | 0 | 0 |
| hardening-stage4-components-retry.xml | 44 | 0 | 0 | 0 |
| hardening-stage5-components-retry.xml | 46 | 0 | 0 | 0 |
| hardening-stage5-components.xml | 45 | 1 | 0 | 0 |
| hardening-stage5-final.xml | 82 | 0 | 0 | 0 |
| hardening-stage5-release.xml | 83 | 0 | 0 | 0 |
| hardening-stage5.xml | 41 | 0 | 0 | 0 |

The two `-k smoke` invocations (`smoke-details`, `smoke-reachability`) each select three checks; saved command output records **13 deselected** for each. Deselected tests are not claimed as executed.

| Browser invocation | Passed | Failed | Skips |
|---|---:|---:|---:|
| hardening-stage4-browser.json | 1 | 0 | 0 |
| hardening/final-browser/run-01.json | 1 | 0 | 0 |
| hardening/final-browser/run-02.json | 1 | 0 | 0 |
| hardening/final-browser/run-03.json | 1 | 0 | 0 |
| hardening/final-browser/run-04.json | 1 | 0 | 0 |
| hardening/final-browser/run-05.json | 1 | 0 | 0 |
| hardening/final-browser/run-06.json | 1 | 0 | 0 |
| hardening/final-browser/run-07.json | 1 | 0 | 0 |
| hardening/final-browser/run-08.json | 1 | 0 | 0 |
| hardening/final-browser/run-09.json | 1 | 0 | 0 |
| hardening/final-browser/run-10.json | 1 | 0 | 0 |

Build invocation ledger: stage 2 PASS; initial stage 4 FAIL (TypeScript rejected two new test options; no React tests ran); stage 4 retry PASS; stage 5 initial build PASS (its React invocation failed separately); stage 5 retry PASS; final build PASS. **Five builds passed, one failed**. No failures were overwritten.

## Smoke and preserved failures

| Actual smoke artifact | Passed checks | Failed checks | Duration ms |
|---|---:|---:|---:|
| hardening-runtime-smoke.json | 7 | 2 | 6875 |
| hardening-release-runtime-smoke.json | 7 | 2 | 14156 |
| hardening-reachability-runtime-smoke.json | 8 | 2 | 25593 |

The final 25,593 ms smoke passed health/migration readiness, coordinator demo scope, reset/default date, Amira IN_WINDOW, uncertain hold, live configuration, authenticated-header catalog reachability and replay configuration. It made zero generation requests. It failed both explanation acceptance checks: current local Amira context does not match the curated source snapshot (`replay_recording_missing_or_context_changed`); uncertain replay faithfully returns `incomplete_response`/insufficient evidence. No records or versions were erased to force a match. Local backend remains explicitly in replay mode with open demo clinical work.

Preserved failure evidence:

- `hardening-recording-setup-failure.json`: the first recorder setup got existing diagnostic-gate HTTP 403, then Windows SQLite cleanup WinError 32; zero provider calls. The temporary process now enables fixture test mode and disposes its connection before cleanup; the application gate is unchanged.
- `hardening-stage4-build-failure.txt`: two invalid Testing Library options caused the initial build failure; corrected in test code.
- `hardening-stage5-components.xml`: **45 passed / 1 failed**. The new coordinator-only error test mistakenly mounted a viewer; corrected fixture role, with authorization unchanged. Retry and final React runs passed 46.
- All original and approved live run result/capture files, including the budget, incomplete-response and timing-guard failures. Original captures were never overwritten.
- Earlier offline matching failures below. Final matching fixes preserve full clinical snapshot and original request-hash checks; no tool results are injected from recordings.
- All smoke JSONs, CLI logs, browser per-run reports and original prior-task browser artifacts remain under their existing ignored directories. No new browser failures occurred in this task.

| Offline verification artifact relative to backend/demo-replays/ | Case | Matched its live result |
|---|---|---|
| hardening-v1\history-amira-replay-1795188291389729200-result.json | history-amira | PASS |
| hardening-v1\tsp-amira-replay-1795188282994224700-result.json | tsp-amira | PASS |
| hardening-v1\tsp-uncertain-replay-1795188299539920200-result.json | tsp-uncertain | PASS |
| history-amira-replay-1795187173364708900-result.json | history-amira | FAIL |
| history-amira-replay-1795187299360172500-result.json | history-amira | FAIL |
| tsp-amira-replay-1795187167476934000-result.json | tsp-amira | FAIL |
| tsp-amira-replay-1795187292297947200-result.json | tsp-amira | FAIL |
| tsp-amira-replay-1795187385700534700-result.json | tsp-amira | FAIL |
| tsp-amira-replay-1795187393266235100-result.json | tsp-amira | FAIL |
| tsp-uncertain-replay-1795187757000566200-result.json | tsp-uncertain | FAIL |
| tsp-uncertain-replay-1795187891881393900-result.json | tsp-uncertain | PASS |

## Files changed and remaining gaps

29 implementation/data/test files plus this report:

- `.env.example`
- `.gitignore`
- `RUNBOOK.md`
- `backend/app/investigation/graph.py`
- `backend/app/investigation/provider.py`
- `backend/app/investigation/replay.py`
- `backend/app/investigation/service.py`
- `backend/app/investigation/tooling.py`
- `backend/app/prevention/tsp_demo.py`
- `backend/demo-replays/hardening-v1/README.md`
- `backend/demo-replays/hardening-v1/history-amira-result.json`
- `backend/demo-replays/hardening-v1/history-demo-amira.json`
- `backend/demo-replays/hardening-v1/tsp-amira-result.json`
- `backend/demo-replays/hardening-v1/tsp-demo-amira.json`
- `backend/demo-replays/hardening-v1/tsp-demo-tsp-uncertain.json`
- `backend/demo-replays/hardening-v1/tsp-uncertain-result.json`
- `backend/tests/test_hardening.py`
- `backend/tests/test_workflow.py`
- `docs/DEMO_HARDENING.md`
- `frontend/e2e/journey.spec.ts`
- `frontend/src/ClinicalExplorer.tsx`
- `frontend/src/History.test.tsx`
- `frontend/src/History.tsx`
- `frontend/src/Jury.test.tsx`
- `frontend/src/Jury.tsx`
- `frontend/src/Tsp.test.tsx`
- `frontend/src/Tsp.tsx`
- `scripts/record_demo_llm.py`
- `scripts/smoke_demo.py`

The six curated JSON files were scanned against private local API keys and role tokens before commit and again before tagging; no matches. Opaque encrypted reasoning and authorization headers are excluded. Local `.env` credentials were not modified or committed.

Remaining gaps: no accepted live clinical explanation was obtained under the existing limits/guards; replay faithfully reproduces those failures. Changed or additional source versions/policies/dates require an appropriate new real capture, never an automatic fallback. Replay supports these bounded TSP/history scenes, not arbitrary/multi-agent investigations. A live catalog check establishes network reachability, not inference quality. Clinical confirmation and production/integration readiness remain outside this synthetic prototype's demonstrated scope.
