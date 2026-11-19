# Single-agent versus multi-agent evaluation

Final matched live report: test-reports/multi-live-20261119-230124-e75d21/summary.json. Each pair used the same objective, authorized decision binding, synthetic PostgreSQL evidence snapshot and evaluation checks. Both used the exact permitted Gemini ID, Responses, 4,000 output tokens and low reasoning effort. These explicit benchmark settings differ from the historical default single-agent settings; historical comparisons alone are not causal evidence.

| Case | Mode | Model calls | Tool calls | Input tokens | Output tokens | Latency ms |
|---|---|---:|---:|---:|---:|---:|
| Complete | Single | 6 | 7 | 18729 | 846 | 21180 |
| Complete | Multi | 4 | 3 | 14449 | 1874 | 21596 |
| Conflicting | Single | 6 | 6 | 22155 | 975 | 32282 |
| Conflicting | Multi | 7 | 4 | 25503 | 3185 | 45741 |
| Missing prerequisite | Single | 6 | 6 | 22287 | 610 | 38975 |
| Missing prerequisite | Multi | 5 | 4 | 16283 | 1446 | 21813 |

Across these three cases, single used 18 calls, 19 tools, 63,171 input + 2,431 output tokens and 92,437 ms. Multi used 16 calls, 11 tools, 56,235 input + 6,505 output tokens and 89,150 ms. Total tokens were 65,602 versus 62,740 (4.4% lower); aggregate latency was 3.6% lower. Output tokens increased substantially. The conflicting case regressed in calls, tokens and latency. Three unreplicated cases cannot establish general superiority or a reliable performance distribution.

All six final runs passed source ownership/version/digest, exact excerpt/structured-value fidelity, real response metadata, authorized tool execution, human-review submission and unchanged clinical state checks. All three multi packets had complete validated selected-agent outputs. Complete evidence did not abstain; conflicting and missing-prerequisite evidence abstained appropriately. The multi packet exposes configured prerequisite states and separate specialist findings. No claim of semantic clinical correctness follows from valid citations.

A separately retained full M08/correction dataset run used 7 calls, 46,446 input + 4,331 output tokens and 50,582 ms. It is more expensive than the historical Increment 1 run and not a matched comparison. It exposes real correction lineage and conflict abstention for UI review. This is further evidence against a blanket optimization claim.

Synthetic evaluation uses labeled deterministic test doubles solely in tests, never fallback providers. Final artifact: test-reports/multi-eval-20261119-231724-44ba03 (34 checks passed). The suite covers all 20 requested scenario categories plus structured-value, chronology and prerequisite-integrity attacks, caching, replay, review guards and provider wire compatibility. Three matched synthetic comparisons measure the same source snapshot and retain both workflows. The existing single-agent path remains available explicitly. It is not automatically selected after specialist failure.

Release recommendation: CONDITIONAL GO for the local synthetic multi-agent capability. Retain the explicit single-agent option and evaluate larger repeated samples before making multi-agent the default or claiming better clinical performance.
