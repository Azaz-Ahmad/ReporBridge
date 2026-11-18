# OpenAI integration

The implementation uses official openai Python SDK 2.54.0, declared as openai>=2.54,<3. OpenAIProvider calls client.responses.create with store=False, parallel_tool_calls=False, a strict Draft JSON schema and seven strict function definitions. The configurable default model is gpt-4.1-mini. This default supports Responses, function calling and structured output according to its official model documentation.

## Configuration

| Environment variable | Default or behavior |
|---|---|
| OPENAI_API_KEY | Required secret, read only in backend |
| OPENAI_BASE_URL | https://api.openai.com/v1 when unset or blank |
| OPENAI_MODEL | gpt-4.1-mini |
| OPENAI_TIMEOUT_SECONDS | 30, validated range 1–60 |
| OPENAI_MAX_OUTPUT_TOKENS | 2400, range 256–6000 per response |
| OPENAI_MAX_TOOL_CALLS | 8, range 1–16 per investigation |
| OPENAI_MAX_AGENT_STEPS | 6, range 2–10 model turns |
| OPENAI_MAX_RUN_COST_USD | Empty by default. Configuring it disables runs with cost_limit_unavailable |
| CLINICAL_EVIDENCE_AGENT_ENABLED | false |

The elapsed-time guard is 180 seconds between model calls. An already executing bounded SDK request may finish after that guard. The SDK timeout bounds individual requests.

The prototype has no maintained model-price catalog. Usage tokens are recorded when the response provides them. Cost estimates remain null. A configured dollar ceiling fails closed because reliable dollar enforcement is unavailable.

The provider status endpoint reports configuration readiness. An available configuration still needs a successful real API request to establish provider connectivity and model access.

## Custom OpenAI-compatible endpoints

The backend validates OPENAI_BASE_URL, passes it explicitly to the official SDK and persists it with each run configuration. The provider status response includes the selected endpoint. The request continues to use Responses, seven authorized function tools and the strict Draft output schema.

For OpenRouter, configure the ignored local .env file with OPENAI_BASE_URL=https://openrouter.ai/api/v1 and OPENAI_MODEL=openai/gpt-4.1-mini. Store the OpenRouter credential only as OPENAI_API_KEY in that ignored file, enable CLINICAL_EVIDENCE_AGENT_ENABLED and restart the backend. Keep .env.example credential-free.

URLs must use HTTP or HTTPS and exclude embedded credentials, query strings and fragments because endpoint configuration is visible in status and run records. An unset or blank URL selects the official OpenAI endpoint. Invalid endpoint configuration disables invocation with invalid_configuration.

See V05_S2_CUSTOM_PROVIDER_VERIFICATION.md for the custom endpoint regression and live verification results. OpenRouter documents POST /api/v1/responses, but account guardrails and upstream model/provider capabilities still require live verification.

[OpenRouter Responses reference](https://openrouter.ai/docs/api/api-reference/responses/create-responses)

## Provider failures

The SDK's implicit retries are disabled. The adapter permits one bounded retry for rate limits and server errors. Timeout, connection, authentication, incomplete response and malformed structured output fail with classified codes. Timeout and connection failures are not automatically replayed. No clinical write operation is exposed as a tool.

Provider error bodies and credentials are excluded from persisted error records. Completed responses contribute reported token counts. Failed or uncertain requests mark usage incomplete, and any usage available on malformed/incomplete responses is preserved. model_calls counts application invocations, retries counts additional attempts.

## Live verification

No OPENAI_API_KEY was configured during this implementation. The agent is disabled in the running app. The repeatable live command recorded BLOCKED and zero successful live runs.

From the repository root, configure the ignored local .env file, enable the agent and restart the backend. Then run `.venv\Scripts\python.exe scripts/verify_clinical_agent_live.py`. It performs three bounded investigations in disposable PostgreSQL schemas, covering complete, missing and conflicting synthetic evidence. It never resets the live Amira workflow.

## Official references

[OpenAI Python SDK](https://github.com/openai/openai-python)

[Responses create reference](https://developers.openai.com/api/reference/python/resources/responses/methods/create)

[Function calling](https://developers.openai.com/api/docs/guides/function-calling)

[Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

[GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
