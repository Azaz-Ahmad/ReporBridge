# Ajyra AI - ReproBridge: disclosure

Synthetic demonstration only; pending clinical confirmation. No real patient data is used. Only synthetic data reaches any runtime model provider. Hospital A and Hospital B are generic labels in a SIMULATED local provider exchange; there is no live institutional connection.

## Baseline and additions

Earlier baseline: `de5e9d3effba97669f93e79181f66e53974c8e17` (multi-agent routing, sealed context and execution accounting). The requested development period starts 16 November 2026; Git records this baseline and the tags below on **20 November 2026, Asia/Dubai**. Those timestamps do not establish which changes were made on 16 November.

| Existing tag | Addition after the baseline |
|---|---|
| tsp-v1 | Data-defined timing windows, dating uncertainty holds, session demo clock and evidence-gated completion classification. |
| handoff-v1 | Clearly simulated Hospital A → B exchange, original provenance and correction-driven reopening. |
| dashboard-v1 | Plain three-patient jury cohort, urgency-first dashboard, admin drawer and role switcher. |
| history-handoff-v1 | Data-defined earlier finding, pending W1 rule, source/facility views and grounded explanation restrictions. |
| history-handoff-v2 | Chronology corrected to the 2011 source at age 16; pregnancy dates unchanged. |
| hardening-v1 | Environment-selected provider, explicit live/replay profiles, guarded recordings, reset safety and smoke/runbook. Its accepted-live-explanation gate was NO GO; preserved failures are not successful live captures. |
| explanation-v1 | One no-tools structured explanation call, exact server-field comparisons, server rendering and labelled abstention fallback; two accepted Claude live calls. |
| demo-v1 | Consistent presentation, successful fresh-history replay capsule, repeatable captures, live reliability evaluation and fresh-clone release QA. See RELEASE_NOTES.md for actual gates and limits. |

The follow-up navigation fix between history-handoff-v2 and hardening-v1 waits for the committed POST result before changing pages. It is not a separate tag. No tags were moved, and this release is not merged or pushed automatically.

## AI development and runtime

OpenAI Codex was used to inspect and implement code, prepare tests/scripts and documentation, investigate failures and run verification. Its exact underlying development-model identifier is not attested by repository evidence. Human authorization and clinical confirmation remain separate from AI-generated development work.

Runtime transport is the existing OpenAI-compatible adapter against `OPENAI_BASE_URL`; this environment uses OpenRouter. Configuration chooses `OPENAI_MODEL` for tool-using investigations and `EXPLANATION_MODEL` for bounded window/history explanations. Neither model is selected silently.

* Explanations evaluated for this release: requested `anthropic/claude-sonnet-5.5-20260928`, provider-reported `anthropic/claude-sonnet-5.5`. Ten genuine live requests per explanation type; no tool calls or retries. Successful replay capsules record their exact model, source context, schema, tokens and provenance.
* Original evidence and multi-agent investigations remain configured with `google/gemini-3.8-flash-20260902` (provider alias `google/gemini-3.8-flash`). They retain the seven authorized M08 tools and original LangGraph workflows. This release's 20-call reliability evaluation covers explanations, not a new live investigation evaluation.
* `openai/gpt-6-luna-20260922` was listed as permitted during earlier authenticated model discovery; it was not used in this release evaluation. No automatic model switching occurs.

Replay is recorded real model output passed through the same field/grounding checks. It is not a new live inference. A mismatching recording abstains; deterministic output is explicitly labelled **Rule-generated explanation (agent abstained)**. Accepted explanation output remains partially grounded and requires human review. Agents cannot change windows, eligibility, relevance, clinical approvals or closure.

Credentials stay in ignored local configuration. Screen captures start after authentication and contain synthetic UI only. Live evaluation traces and original failure artifacts remain under ignored test-reports; public summaries contain no tokens or keys.
