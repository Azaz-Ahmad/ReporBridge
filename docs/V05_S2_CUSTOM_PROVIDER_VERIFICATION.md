# Custom OpenAI-compatible provider verification

This historical report covers the earlier key restriction on openai/gpt-4.1-mini. Current permitted Gemini configuration and successful live verification are recorded in V05_S2_GEMINI_VERIFICATION.md.

The adapter now reads OPENAI_BASE_URL, validates it, passes it explicitly to the official OpenAI SDK and includes it in provider status and persisted run configuration. An unset or blank value defaults to https://api.openai.com/v1. The Responses request format, strict Draft schema, LangGraph investigation, seven authorized M08 tools and grounding/review controls use their existing implementations.

The configured local endpoint is https://openrouter.ai/api/v1 with model openai/gpt-4.1-mini. The authenticated running backend reports status available, which represents valid local configuration. Upstream model eligibility is established by actual requests.

The supplied credential was initially saved in .env.example. It was transferred into the ignored .env file and cleared from the template before staging any changes.

## Live investigations

The three required synthetic investigations were attempted through the real OpenRouter Responses endpoint in disposable PostgreSQL schemas. Each run persisted its failure trace, and the trace endpoint retrieved those records before schema cleanup. Artifacts are in test-reports/openai-live-20261118-233040/summary.json.

| Case | Result | Actual tool executions | Grounding |
|---|---|---|---|
| Complete evidence | Provider routing failed | 0 | insufficient_evidence, system abstention |
| Missing evidence | Provider routing failed | 0 | insufficient_evidence, system abstention |
| Conflicting evidence | Provider routing failed | 0 | insufficient_evidence, system abstention |

A further bounded synthetic diagnostic request captured the exact upstream error in test-reports/openrouter-compatibility-error.json.

HTTP 404, provider code 404, ineligibility reason model-ignored-by-guardrail.

> 0 endpoints out of 2 requested are available matching your guardrail restrictions and data policy. We removed them for the following reasons (an endpoint may have matched multiple reasons):
> Model blocked by guardrail: 2 endpoints excluded; configurable at https://openrouter.ai/workspaces/default/guardrails

The routing metadata identifies the failed step as Filter by Guardrails. This account restriction prevented live model inference, model-selected function calls and structured output validation. Successful live investigations total zero. It provides no evidence of a Responses parameter incompatibility, so the adapter retains its existing request schema and execution safeguards.

The account owner was asked to allow the requested model in the OpenRouter workspace guardrail. Re-run the three-case live command after that change.

## Automated verification

The focused investigation suite passed 37 tests, including nine added cases. They check official endpoint fallback, blank and normalized URLs, invalid/credential-bearing URLs, status redaction and actual SDK routing to /api/v1/responses on the custom host.

The custom SDK integration test uses explicitly isolated HTTP MockTransport. It exercises function-call parsing, actual M08 retrieval, strict structured output, source grounding, usage and persisted trace retrieval. This test is distinct from the unsuccessful real OpenRouter runs.

Full regression artifacts are in test-reports/20261118-233308-95ecfbe1. Both PostgreSQL and supplementary SQLite passed 90 tests. The production build passed, all 12 React component tests passed, both PostgreSQL browser journeys passed and both FHIR exports validated. The completed summary.json records every automated gate.

## Release decision

CONDITIONAL GO for configurable endpoint support. The OpenRouter live milestone remains blocked by the account guardrail. An unconditional release requires successful complete, missing and conflicting real investigations and inspection of their tool selection, grounding and traces.

[OpenRouter Responses reference](https://openrouter.ai/docs/api/api-reference/responses/create-responses)
