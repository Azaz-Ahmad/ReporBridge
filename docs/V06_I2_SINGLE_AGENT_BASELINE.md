# Recorded single-agent baseline

Inspected Sprint 2 openai-live-20261118-235154-39baee and both v06-live directories. Sprint 2 complete: 6 model calls, 5 tools, 17,873 input / 2,036 output tokens, 30,808 ms. Three observation searches plus provenance/quality read the same observation. Missing and conflicting cases routed to human review. Full traces retain source/version and validation metadata.

Increment 1 accepted run investigation-4be08f8029e44cc5a211917843e365ff: 6 calls, 5 tools, 35,316 input / 2,466 output, 42,514 ms. Context was listed twice with overlapping records. Document search returned no sections. Conflicting evidence required abstention; narrative remained partially grounded and clinical state unchanged.

Earlier actual run investigation-c28114489f2241f7a57443e79bb2745c: 6 calls, 5 tools, 25,672 input / 985 output, 46,368 ms. unknown_citation and conflict_not_acknowledged rejected its output; unsupported findings were withheld. These were validation errors, not successful runs.

Tool reads took tens to hundreds of milliseconds; model calls and expanding history dominated latency. Historical cases do not prove optimization. Matched-snapshot comparisons must report additional specialist cost and any regressions. Valid citations do not establish clinical completeness.
