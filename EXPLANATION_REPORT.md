# Explanation v1 implementation and verification

**GO for the bounded synthetic explanation demo.** Two real single-call explanations were accepted; original grounding status is `partially_grounded` with no errors and mandatory human review. This is not clinical certification or production approval.

Branch: `feat/explanation-fix`, from `hardening-v1` / `cc7d913`. Stages committed as `ed34a1d`, `f48fdad`, `0ec8825`; this final report/UI commit receives annotated tag `explanation-v1`. No merge, push, history rewrite or previous-tag change.

Time box: work began **2026-11-20 20:08:58 Asia/Dubai**; all verification including real-UI checks completed by **21:05:55** (56m57s). The two-hour deadline is 22:08:58. Report/tag preparation remains inside that limit.

## Exact causes of the five original abstentions

| Preserved run | Actual recorded cause |
|---|---|
| Initial TSP | Nine tool calls requested; eight executed. `authorized_tools` rejected the ninth at the eight-call budget, before a final Draft could be obtained. |
| Initial historical | Turn 3 returned a non-completed Responses result; adapter raised `incomplete_response`. Last-turn output: 2,393 tokens against a 2,400 cap. |
| Uncertain dating | Turn 6 returned a non-completed Responses result; same rejection. Last-turn output: 2,385 tokens against 2,400. |
| Repeat TSP | The summary exactly matched the server. Narrative findings added dates, and missing-information/review text added window W1 outside the exact summary/literal value, causing `tsp_window_or_policy_mismatch`. |
| Repeat historical | Turn 5 returned a non-completed Responses result; same rejection. Last-turn output: 2,393 against 2,400. |

The original traces did not retain `incomplete_details` or a reasoning-token split. Token exhaustion is strongly suggested by near-cap output, but its precise upstream reason cannot be proved from the saved metadata. No missing detail is invented. `scripts/analyze_explanation_failures.py` reproduces the read-only analysis in `test-reports/explanation/five-causes.json`; the offending TSP fields are retained there. Future incomplete failures now persist response status, reason, cap and reasoning-token metadata when supplied by the provider.

## Allowed models and explicit selection

Authenticated read-only `/models/user` and catalog queries returned these key-visible canonical IDs. Ranking uses the provider-reported Artificial Analysis intelligence index, not a clinical-validation claim:

| Model | Reported index |
|---|---:|
| anthropic/claude-sonnet-5.5-20260928 | 54.5 |
| google/gemini-3.8-flash-20260902 | 30.8 |
| openai/gpt-6-luna-20260922 | 27.9 |

Selected explicitly: **anthropic/claude-sonnet-5.5-20260928**, the highest ranked among those three. Its provider-reported alias is `anthropic/claude-sonnet-5.5`. The ignored `.env` now sets `EXPLANATION_MODEL`; the generic evidence agent's `OPENAI_MODEL` and all credential values are preserved. No model is hard-coded as an application default or switched automatically. Discovery/ranking evidence is in `model-discovery.json` and `model-ranking.json`; private account/key values were not dumped. [Catalog API documentation](https://openrouter.ai/docs/api/api-reference/models/get-models).

## Implemented behavior and preserved safety

- User-facing TSP/history buttons call additive `/explanations` routes. Legacy `/investigations` routes and the original six-node graph/seven M08 tools remain available and regression-tested.
- Server authorization and synthetic identity/source-tag checks precede context preparation. The packet includes calculator status, dates, policy/version/citation, and versioned/digested cited excerpts/rule fields. No raw request question can change that trusted context.
- Exactly **one** Responses request, no retries, `tools=[]`, `tool_choice=none`. Closed strict schema: at most two windows, eight cited records, four rules, 240-character excerpts, total context capped at 12,000 characters, 6,000 output tokens and 60-second timeout. The two live outputs fit comfortably below the cap and completed.
- Every returned field/type is compared exactly with authoritative calculator/source data, including every date, number, status, policy identifier/version, source digest/version/excerpt and review flag. Unknown/free prose is forbidden. The server renders final text from the matched fields; the original grounding, source freshness and human-review checks still run. The tool node is skipped by this path because there are no tool calls; the registered six-node workflow itself is unchanged.
- Model refusal, mismatch, missing replay, disabled/unavailable provider or provider failure remains a logged abstention. A separate fresh-context fallback is labelled **Rule-generated explanation (agent abstained)** and visible with the trace; its packet remains `system_abstention`, not accepted model output. If context changes during the call, fallback text is withheld until reload.
- Original M08 contracts, patient grants/authorization, grounding implementation, closure gates, history/risk rules, deterministic timing calculator and citation placeholder are unchanged. The optional reservation flag permits logging a zero-call rule fallback when a provider is unavailable; it never permits model execution while unavailable. No migrations/dependencies were added.

## Actual live and replay results

| Live case | Round-trip latency ms | Input tokens | Output tokens | Model requests | Tools | Field mismatches / original grounding errors |
|---|---:|---:|---:|---:|---:|---|
| history | 14937 | 3119 | 1091 | 1 | 0 | 0 / 0 |
| tsp | 12682 | 2667 | 655 | 1 | 0 | 0 / 0 |

Exactly **two live generation requests** were made in this task. Both were accepted with complete reported usage, zero retries, `partially_grounded`, `interpretation_required=false`, and required human review. No uncertain-dating live call is claimed or charged by this task.

Only those two successful real responses were installed under `backend/demo-replays/explanation-v1/`; diagnostic result files are ignored. Keys, role tokens and headers are excluded; the two files were scanned against local private key/token values before inclusion and final release. Original hardening failures/captures remain untouched in their original directories/tag and are not the new explanation replay path.

After reset, both accepted recordings were revalidated against current authorized source versions/digests and the original grounding: accepted, one replay turn each, **zero live calls/tokens/tools**. The uncertain-dating scene intentionally uses the correctly labelled rule fallback and keeps its hold; no successful uncertain live recording is invented. A separate headless public-app UI check confirmed both accepted replay labels/text actually display, with zero live calls/tools, without tracing/video or credential-bearing artifacts (`accepted-ui.json`, `accepted-ui.png`).

## Exact test counts per invocation

All XMLs are under `test-reports/explanation/`; each row is a distinct invocation, not a count of unique tests across reruns.

| Artifact | Passed | Failed | Errors | Skips |
|---|---:|---:|---:|---:|
| backend-stage2.xml | 92 | 0 | 0 | 0 |
| components-stage2.xml | 48 | 0 | 0 | 0 |
| full-components.xml | 48 | 0 | 0 | 0 |
| full-postgres.xml | 272 | 0 | 0 | 0 |
| full-sqlite.xml | 272 | 0 | 0 | 0 |
| smoke-unit.xml | 3 | 0 | 0 | 0 |
| unit-final.xml | 17 | 0 | 0 | 0 |
| unit-first.xml | 13 | 0 | 0 | 0 |
| unit-synthetic-guard-retry.xml | 18 | 0 | 0 | 0 |
| unit-synthetic-guard.xml | 17 | 1 | 0 | 0 |

`smoke-unit.xml` selected 3 checks and **13 deselected**; those deselected tests are not claimed as executed. Both production-build invocations (stage 2 and final) passed.

| Complete browser invocation | Passed | Failed | Skips |
|---|---:|---:|---:|
| browser-stage3.json | 1 | 0 | 0 |
| final-browser/run-01.json | 1 | 0 | 0 |
| final-browser/run-02.json | 1 | 0 | 0 |
| final-browser/run-03.json | 1 | 0 | 0 |
| final-browser/run-04.json | 1 | 0 | 0 |
| final-browser/run-05.json | 1 | 0 | 0 |
| final-browser/run-06.json | 1 | 0 | 0 |
| final-browser/run-07.json | 1 | 0 | 0 |
| final-browser/run-08.json | 1 | 0 | 0 |
| final-browser/run-09.json | 1 | 0 | 0 |
| final-browser/run-10.json | 1 | 0 | 0 |

Final browser sequence: **10 consecutive passes**, zero retries/skips/flaky results. Each uses fresh synthetic SQLite and preserves the original journey/clinical approval/verified closure assertions. Added checks prove the exact fallback label, visible abstention trace, zero live calls/no tools and 390px layout. The framework journey retains its original disabled-agent setting; real accepted live/replay endpoints and the public UI are separately verified, not falsely counted as ten live model runs.

Full regression: **272 SQLite**, **272 PostgreSQL**, **48 React** passed; no failures/errors/skips. The original 254 backend and 46 React tests remain, plus 18 bounded-explanation cases and two presentation cases.

## Smoke and preserved failures

| Actual smoke | Passed | Failed | Duration ms | Generation requests |
|---|---:|---:|---:|---:|
| smoke-first.json | 12 | 0 | 15156 | 0 |
| smoke-final.json | 12 | 0 | 33500 | 0 |

Both are below the 60-second budget. They verify health/head migration 0009, coordinator synthetic scope, reset/default date, Amira IN_WINDOW, uncertain hold, live catalog reachability, accepted window/history replay, and explicitly labelled uncertain fallback. The final backend remains in explicit replay mode with open demo work. No explanation closes an obligation.

Preserved new failure: `unit-synthetic-guard.xml` records **17 passed / 1 failed** because the negative test incorrectly expected ingestion of an untagged resource to succeed. M08 correctly returned 422. The test now asserts that 422, then simulates an untagged external-provider result to verify the new projection guard also rejects it before any model call. Retry passed 18/18. No production safeguard was weakened or made to accept that resource.

All five original live failures, the old hardening build/React/recorder/replay/smoke failures and previous browser artifacts remain preserved. There were no new live, smoke, build, React or browser failures in this task. Full per-run JSONs, logs and framework artifacts remain under ignored test-reports.

## Files changed and known limits

26 implementation/data/test files plus this report:

- `.env.example`
- `.gitignore`
- `RUNBOOK.md`
- `backend/app/explanations.py`
- `backend/app/history_api.py`
- `backend/app/investigation/provider.py`
- `backend/app/investigation/service.py`
- `backend/app/prevention/tsp_api.py`
- `backend/demo-replays/explanation-v1/README.md`
- `backend/demo-replays/explanation-v1/history-demo-amira.json`
- `backend/demo-replays/explanation-v1/tsp-demo-amira.json`
- `backend/tests/test_explanations.py`
- `backend/tests/test_hardening.py`
- `docs/EXPLANATION_DIAGNOSIS.md`
- `docs/EXPLANATION_V1.md`
- `frontend/e2e/journey.spec.ts`
- `frontend/src/ExplanationOutput.test.tsx`
- `frontend/src/ExplanationOutput.tsx`
- `frontend/src/History.test.tsx`
- `frontend/src/History.tsx`
- `frontend/src/Tsp.test.tsx`
- `frontend/src/Tsp.tsx`
- `frontend/src/style.css`
- `scripts/analyze_explanation_failures.py`
- `scripts/record_explanations.py`
- `scripts/smoke_demo.py`

This is a bounded exact-field explanation path, not a general medical reasoning system. Sources/policies/dates outside a matching recording require a new accepted capture or the visibly labelled deterministic fallback; stale context suppresses that fallback. The legacy open-ended/tool-based evidence investigation keeps its existing budgets and behavior. Clinical confirmation and production/institution integration readiness remain outstanding. Source corrections, clinical approvals, patient authorization and evidence-verified closure stay with the original services.
