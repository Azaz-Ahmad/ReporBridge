# Matched optimization evaluation

Source: test-reports/i21-live-20261119-235430-cc3594/summary.json and analysis.json. Two live repetitions per primary scenario per profile: 12 primary runs. Mode order was counterbalanced. Each scenario used the same patient, source IDs/versions/hashes, decision binding, question, strict contracts, model, 4,000-token output ceiling and low reasoning effort. The source fingerprint and clinical state were unchanged within every comparison. The baseline is the frozen verified Increment 2 implementation, with common nonsemantic invocation instrumentation.

| Scenario | Profile | Calls | M08 executions | Mean input tokens | Mean output tokens | Mean elapsed s |
|---|---|---:|---:|---:|---:|---:|
| Complete | Legacy | 6 | 5 | 22,806.5 | 2,094.5 | 33.982 |
| Complete | Optimized | 2 | 2 | 5,322 | 547 | 9.851 |
| Conflicting | Legacy | 7 | 3 | 27,490.5 | 2,935 | 38.347 |
| Conflicting | Optimized | 3 | 2 | 8,877.5 | 1,314 | 15.402 |
| Missing prerequisite | Legacy | 6 | 4 | 20,116.5 | 1,840 | 30.435 |
| Missing prerequisite | Optimized | 4 | 3 | 9,170 | 889 | 15.878 |

Across the six primary runs per profile, input tokens fell from 140,827 to 46,739: **66.8% lower**, exceeding the 15% target. Output tokens fell from 13,739 to 5,500. Model calls fell 38 to 18 and actual M08 executions 24 to 14. Conflict mean elapsed time fell 38.347 to 15.402 seconds: **59.8% lower**, exceeding the 20% target. No dollar estimate is made because no reliable pricing is configured.

All 12 primary runs passed exact citation/version/hash ownership, structured-value fidelity, appropriate abstention, mandatory human-review submission, unchanged model, actual authorized tools and unchanged clinical state. All selected agent outputs validated. Complete evidence proposed source facts without readiness abstention; conflicting and missing-prerequisite cases abstained. Clinical completeness and semantic correctness are not inferred from citation validity.

A separate corrected/conflicting chronology scenario kept routing and source context fixed and compared optimized serial versus optimized parallel twice each. All four runs passed safety/grounding gates. Mean elapsed time was 27.525 seconds serial and 20.151 parallel: **26.8% lower**. Both modes used four model calls. Primary-case gains must chiefly be attributed to reduced routing/retrieval/context, not to concurrency, because only one specialist was needed there.

Two repetitions per mode are a small sample, not an SLA or clinical-quality trial. Model/provider variability is visible: legacy complete ranged 28.252–39.711 seconds, while optimized complete ranged 8.853–10.849; legacy conflict 35.741–40.952 versus optimized 15.133–15.670. These results should not be generalized to unmeasured objectives, source sizes or production concurrency.

The deterministic suite separately records 10 matched categories—complete, conflict, missing prerequisite, corrected, superseded, injection, wrong patient, stale evidence, tool failure and provider failure—plus 28 focused safety/context/cache/routing/concurrency/accounting checks. Test-double tokens/latencies are not represented as live measurements. Artifacts: test-reports/i21-eval-20261120-001514-591f82.

A full-M08 retained app run used four real model calls, four tool executions, 17,101 input / 1,796 output tokens and 30.024 seconds. It found conflicts and entered pending_review with a complete selected-agent packet. It used a different, larger snapshot under concurrent regression load; it is a UI/observability verification, not a matched performance comparison. Its measured completed checkpoint time was 6.475 seconds, showing that preserved global transaction serialization remains a potential bottleneck under load.
