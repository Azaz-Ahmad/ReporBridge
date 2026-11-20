# Demo provider configuration

Set `CLINICAL_EVIDENCE_AGENT_ENABLED=true` to enable explanations. Set `OPENAI_MODEL` to the exact model ID allowed by your own provider/key. There is no default model and no automatic model switch. `OPENAI_API_KEY` stays in the ignored local `.env` or process environment. Never commit or record it.

`OPENAI_BASE_URL` selects the OpenAI-compatible Responses endpoint; blank/unset uses `https://api.openai.com/v1`. For OpenRouter use `https://openrouter.ai/api/v1`. Rejected models stop with `configured_model_rejected` and an instruction to check `OPENAI_MODEL`; upstream error bodies are not logged.

Existing bounds: `OPENAI_TIMEOUT_SECONDS` (30), `OPENAI_MAX_OUTPUT_TOKENS` (2400), `OPENAI_MAX_TOOL_CALLS` (8), `OPENAI_MAX_AGENT_STEPS` (6), optional `OPENAI_REASONING_EFFORT`. A dollar limit is not supported: setting `OPENAI_MAX_RUN_COST_USD` disables execution rather than pretending to enforce cost.
