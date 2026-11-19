# Increment 2.1 baseline audit

Repository F:\ReproBridge was clean at da44aea61ea2bf5aabae621b5735ab42fef8f348. Inspected the ten supervisor nodes, nested six-node A01 graph, all four agent contracts, all seven M08 adapters and underlying ClinicalTools, configured Responses provider, token accounting, source validation, human review, existing synthetic scenarios and retained traces. No applicable AGENTS.md was found.

Before implementation, scripts/Test-Demo.ps1 -PostgreSQL passed 144 tests on each database, 20 React tests, production build, both independent PostgreSQL browser journeys and both FHIR validators. Baseline artifacts: test-reports/20261119-233339-dbad1e69.

Verified historical evidence is test-reports/multi-live-20261119-230124-e75d21/summary.json. Complete: 4 calls / 3 tools / 14,449 input / 1,874 output / 21,596 ms. Conflicting: 7 / 4 / 25,503 / 3,185 / 45,741 ms. Missing prerequisite: 5 / 4 / 16,283 / 1,446 / 21,813 ms. Successful response IDs and the requested/reported models are present; no measurements were inferred from reported prose.

Historical per-call model latency and context size were not recorded. Specialist duration includes additional work, and A01 duration includes its entire nested graph; neither is labeled exact model latency. Fresh matched comparisons instrument these missing fields. The original source is frozen for an explicit legacy comparison/rollback profile, with only its shared-module import redirected to the matching frozen copy. Neither profile is a mock or an automatic fallback.
