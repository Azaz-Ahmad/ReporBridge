# Gemini live verification and release

**GO for the local synthetic Ajyra AI - ReproBridge v0.5 Sprint 2 scope.** All three real model investigations and the mandatory automated safety gates passed.

The starting commit is d60c46d95c2ba243f56292f85aa95b793f03a5b7. The release commit is recorded by git log -1 and the delivery message.

## Actual provider configuration

The active endpoint is https://openrouter.ai/api/v1 and every request uses google/gemini-3.8-flash-20260902. OpenRouter reports google/gemini-3.8-flash in response metadata. Both identifiers and actual response IDs are persisted per model turn. No alternate model was requested.

The other models permitted by the user are anthropic/claude-sonnet-5.5-20260928 and openai/gpt-6-luna-20260922. They were not invoked. The locally configured primary and .env.example now use the exact Gemini ID. The credential remains in ignored .env.

The authenticated running backend reports available, the Gemini model and google_structural profile. The API used successfully is Responses.

## Three required live investigations

Raw proof is saved in test-reports/openai-live-20261118-235154-39baee/summary.json.

| Case | Grounding | Abstained | Independently checked values | Result |
|---|---|---|---|---|
| complete | partially_grounded | false | 1 | PASS |
| missing | insufficient_evidence | true | 0 | PASS |
| conflict | conflicting_evidence | true | 3 | PASS |

| Case | Model calls | Tool executions | Input tokens | Output tokens | Duration ms |
|---|---|---|---|---|---|
| complete | 6 | 5 | 17873 | 2036 | 30808 |
| missing | 5 | 6 | 18005 | 2822 | 53335 |
| conflict | 6 | 5 | 29226 | 2744 | 31986 |

The final gate recorded 17 real model calls, 16 authorized tool executions, 65,104 input tokens and 7,602 output tokens. All responses supplied usage. Retry count was zero. Dollar cost was not estimated.

Each run saved metadata and packet state in PostgreSQL. The trace endpoint retrieved those persisted records. Each packet was submitted into pending_review and read using the reviewer role. Clinical obligations, clinical approvals and closure evidence matched their pre-investigation snapshots. The disposable verification schemas were cleaned up afterward, and the full trace/packet proof remains in the report JSON.

The verifier re-read every cited source under trusted patient scope and checked patient identity, source version and digest. It independently compared four valueString claims with stored structured values. The complete case reviewed the documented outstanding flag. The conflict case retained historical/corrected assessment lineage and unresolved current conflicts. The missing case reported inaccessible document content and abstained.

Actual selected tools included search_patient_observations, search_patient_documents, get_patient_clinical_context, get_evidence_provenance, check_evidence_quality and get_related_obligations. All seven tools, including search_patient_encounters, remain available and are exercised by the regression suite. Model calls can contain multiple functions, and the backend executes them sequentially within its tool budget.

The six graph nodes remain validate_request, investigate, authorized_tools, validate_grounding, prepare_review_packet and human_review_queue. Patient scope comes from the authenticated backend. Tools retain their original schemas, bounds, resource checks and read permissions.

## Compatibility findings and correction

The first Gemini round failed before retrieval because Google rejected the final response schema with HTTP 400. The captured upstream message was

> The specified schema produces a constraint that has too many states for serving. Typical causes of this error are schemas with lots of text (for example, very long property or enum names), schemas with long array length limits (especially when nested), or schemas using complex value matchers (for example, integers or numbers with minimum/maximum bounds or strings with complex formats like date-time)

The diagnostic is retained in test-reports/gemini-responses-diagnostic.json. The google_structural profile removes size/range/format constraints from the serving response schema while retaining its types, enums, required fields and closed objects. The full original Pydantic contracts validate every generated draft locally. Tool schemas and authorization are retained. Invalid output still fails closed.

An intermediate round made real function calls with limit=10. The existing backend cap of eight rejected them and the agent abstained. The serving tool schemas retain their numeric limits, and tool/system descriptions now explicitly state the page cap. No backend cap was increased. The following live round passed all three scenarios, and the final stronger gate independently repeated source/value and review-routing checks.

Responses then passed the live gate. A Chat Completions adapter was unnecessary. No mock substitution or model fallback was used in live verification.

## Regression proof

Command scripts/Test-Demo.ps1 -PostgreSQL completed successfully. Artifacts are in test-reports/20261118-235402-a25db25b.

- PostgreSQL Python tests passed 93 cases.
- Supplementary SQLite Python tests passed 93 cases.
- React components passed 12 cases.
- Production TypeScript/Vite build passed.
- Both independent PostgreSQL browser journeys passed.
- Both downloaded FHIR bundles passed structure and patient-local reference validation.

Focused investigation tests passed 40 cases. Added coverage verifies Google structural serving schemas, preservation of backend bounds, reported/requested model IDs, response IDs and sanitized persisted HTTP errors. Existing tests cover all seven M08 tools, cross-patient rejection, injection-bearing documents, fabricated sources, structured-value tampering, evidence changes, budgets, replay and clinical closure separation.

## Clinical and operational limits

Every generated packet requires human review. Narrative interpretation remains partially grounded even when source IDs and values pass deterministic checks. The missing and conflicting cases abstain from a clinical conclusion. Shared role grants, canonical synthetic Amira scope, local bounded retrieval, synchronous execution and unavailable dollar estimates remain prototype constraints.

Live investigations used only freshly seeded synthetic data. The local Amira clinical workflow was preserved. API keys are excluded from source, report output and default traces.

[OpenRouter Responses reference](https://openrouter.ai/docs/api/api-reference/responses/create-responses)

[OpenRouter structured-output guidance](https://openrouter.ai/blog/tutorials/structured-output-llm/)
