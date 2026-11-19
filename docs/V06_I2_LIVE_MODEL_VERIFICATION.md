# Actual OpenRouter verification

Final batch PASS: test-reports/multi-live-20261119-230124-e75d21/summary.json. Requested model google/gemini-3.8-flash-20260902; every successful provider response reported google/gemini-3.8-flash. The requested identifier never switched. API remained Responses; no Chat Completions or mock fallback was used. Only canonical synthetic records were sent.

Multi run IDs:
- Complete: investigation-cac3253fc1694e5ab54ba61f952824a1, 4 model calls / 3 tools, validated complete packet and no readiness abstention.
- Conflicting: investigation-ee1a71da034b4305b4b20494016086fb, 7 calls / 4 tools, conflicts and appropriate abstention.
- Missing prerequisite: investigation-8e6e90608257457ca1a5c10d73883679, 5 calls / 4 tools, missing prerequisite and appropriate abstention.

Each selected specialist has an actual provider response ID and reported model; skipped specialists have no fabricated call. Sources, exact values, citations, prerequisite status, routing and mandatory human review passed. Each pair used an identical evidence fingerprint. Clinical obligations, approvals and closure state remained unchanged. Reports retain actual model/tool traces, tokens, latency and validation.

The running app also retains investigation-e374f75c361b4b479fd286305ed83462, using the full M08 dataset with genuine corrected/superseded records and conflicts. It completed 7 actual model calls and all three specialists, with 46,446 input / 4,331 output tokens, zero retries and 50,582 ms. It abstained with conflicting_evidence and produced a complete selected-agent packet. A synthetic demo reviewer then recorded request_evidence. test-reports/i2-retained-live.json records before/after clinical-state equality for both investigation and summary review.

## Recorded failures and compatibility adjustments

Earlier batches are preserved in multi-live-20261119-224518-7b102a, 224834-c19516, 225116-6a92bd, 225547-d7ac7d and 225745-f078b0. Some batches were deliberately interrupted after the first completed case to address observed failures. Their completed-case traces remain; interrupted in-flight provider usage may exceed those recorded batch totals.

Actual failures included incomplete_response at the 2,400/4,000 output ceilings, tool_budget_exhausted when Gemini returned multiple function calls despite parallel_tool_calls=false, structured_value_mismatch for unquoted source strings, and support_content_required for metadata-only narrative. Failures yielded partial/abstained packets, never accepted clinical facts.

Adjustments: explicit multi-agent 4,000-token ceiling; documented low reasoning effort to reserve visible-output space; concise contracts/instructions; exact source-generated support templates; exact source-string equality before JSON serialization repair; metadata-only findings withheld with uncertainty and abstention when no supported findings remain; explicit excess-tool denials before final drafting. Wrong values, citations and versions still fail. A verification-harness defect also incorrectly required A01's aggregate metadata to have the specialist response field; the final harness checks specialist responses separately and A01 actual model history independently. Earlier batch results were not rewritten as success.

The configured official OpenAI default/base-URL behavior and original single-agent settings remain backward compatible. New optional OPENAI_REASONING_EFFORT defaults unset; MULTI_AGENT_REASONING_EFFORT defaults low. No credentials are included in reports or screenshots.
