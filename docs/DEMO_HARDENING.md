# Demo provider configuration

Set `CLINICAL_EVIDENCE_AGENT_ENABLED=true` to enable explanations. Set `OPENAI_MODEL` to the exact model ID allowed by your own provider/key. There is no default model and no automatic model switch. `OPENAI_API_KEY` stays in the ignored local `.env` or process environment. Never commit or record it.

`OPENAI_BASE_URL` selects the OpenAI-compatible Responses endpoint; blank/unset uses `https://api.openai.com/v1`. For OpenRouter use `https://openrouter.ai/api/v1`. Rejected models stop with `configured_model_rejected` and an instruction to check `OPENAI_MODEL`; upstream error bodies are not logged.

Existing bounds: `OPENAI_TIMEOUT_SECONDS` (30), `OPENAI_MAX_OUTPUT_TOKENS` (2400), `OPENAI_MAX_TOOL_CALLS` (8), `OPENAI_MAX_AGENT_STEPS` (6), optional `OPENAI_REASONING_EFFORT`. A dollar limit is not supported: setting `OPENAI_MAX_RUN_COST_USD` disables execution rather than pretending to enforce cost.

## Explicit live and replay

`LLM_MODE=live` (default) makes actual Responses API calls. `LLM_MODE=replay` requires `DEMO_MODE=true`, an explicit `OPENAI_MODEL` matching the recording, and real recordings in `LLM_REPLAY_DIR` (default `backend/demo-replays`). Replay never uses the network, never falls back, and fails closed for missing/changed scenarios. The small Replay mode label appears only within the demo Admin drawer.

Replay covers the bounded TSP Amira / exact uncertain-dating fixture and historical Amira explanation routes, not generic or multi-agent investigations. Patient grants, seven tools, six nodes and all original clinical/grounding/closure gates remain in force. The uncertain fixture's exact identity/resource is attested just like canonical Amira; this does not grant access to other patients.

Record actual live turns with `.venv\Scripts\python.exe scripts/record_demo_llm.py`. Select `--cases tsp-amira history-amira` for the two required explanations, or add `tsp-uncertain` to install that replay scenario. The script reads the ignored environment, creates and migrates temporary synthetic-only SQLite databases, limits provider retries to zero, records actual model/tool turns and result metrics, and refuses to overwrite existing recordings. No mock fills absent recordings. `LLM_RECORD_DIR` is used internally for these explicit live captures; leave it unset during ordinary operation. Inspect local files before sharing; authorization/keys, token values and opaque encrypted reasoning are stripped. Local captures are ignored by Git.

Recordings preserve original drafts/tool calls; replay only rebinds opaque evidence/obligation/scope handles after matching the current authorized resource identities, versions, digests, statuses, quality, policy and demo clock. Receipt timestamps/order are transport metadata and normalized only for matching. Clinical values/dates and grounding checks are not changed. Changed source/policy/date or unsupported requests fail closed. Model-reported historic tokens are retained separately; replay incurs zero live model calls/tokens.
