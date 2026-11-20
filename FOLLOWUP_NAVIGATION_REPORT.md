# Follow-up navigation investigation

Branch: `fix/followup-navigation`, from `history-handoff-v2` (`89372e4`). Existing history tags are preserved. No application, API, clinical rule, source data, authorization, grounding or closure implementation changed.

## Root cause

The journey clicked “Initiate follow-up 1” and immediately called `page.goto('/audit')`. Playwright's click completion does not wait for the asynchronous follow-up POST. Full-document navigation can abort that fetch before the server records the event.

The preserved failing trace reports the follow-up POST as status -1, `net::ERR_ABORTED`. Its final three successful prevention snapshot response bodies include `decision_recorded` but no `follow_up_initiated`. This distinguishes the failure from an audit screen displaying stale data after a successful write. The existing audit assertion already retries its text lookup. Source inspection also confirms pending controls are disabled, there is no optimistic audit insertion, and the backend writes the event within the transaction completed before its response is returned.

This is a **test wait-condition race**, not evidence of an application “success before data loads” bug. The preserved historical failure contains direct evidence of cancellation, even though the new ten-run baseline did not reproduce it.

## Minimal fix

Only `frontend/e2e/journey.spec.ts` changes executable test behavior. Register a wait for the exact POST method/path before clicking. Require a successful HTTP response and consume/check the returned decision's follow-up content, then navigate. Both original visible audit assertions (“Decision recorded”, “Follow up initiated”) remain unchanged. No sleeps, retries, larger timeouts or weakened assertions were introduced.

## Preserved evidence

- Original failing report: `test-reports/history-v2-browser.json`.
- Original screenshot/trace: `test-reports/history-v2-browser-failed-artifacts/` (untouched).
- Credential-free diagnosis and original trace SHA-256 hashes: `test-reports/followup-navigation/diagnosis.json`.
- Per-invocation JSON, logs and dedicated artifact directories: `test-reports/followup-navigation/baseline/` and `fixed/`. Generated reports are ignored, not committed.

## Exact runs

Each sequence invokes the complete journey ten times **serially**, one worker, one fresh synthetic SQLite database and new local servers per invocation. No retries are configured. Every journey keeps the original clinical, closure, source, TSP, simulated exchange, historical age-16 and responsive checks. No live LLM requests or existing application data resets are involved.

Unchanged baseline: **10 passed, 0 failed, 0 skipped** (ten distinct invocations, one journey test each).

Fixed sequence: **10 passed, 0 failed, 0 skipped, 0 retries** (ten distinct consecutive invocations, one complete journey test each). All baseline and fixed invocations also report zero unexpected/flaky results. The baseline did not reproduce the intermittent issue; the fix is justified by the preserved failing request/response evidence and the explicit race in the old test.

| Invocation | Baseline | Fixed |
|---|---|---|
| run-01.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-02.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-03.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-04.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-05.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-06.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-07.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-08.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-09.json | 1 passed, 0 failed | 1 passed, 0 failed |
| run-10.json | 1 passed, 0 failed | 1 passed, 0 failed |

| Additional invocation | Passed | Failed | Errors | Skips |
|---|---:|---:|---:|---:|
| sqlite.xml | 238 | 0 | 0 | 0 |
| postgres.xml | 238 | 0 | 0 | 0 |
| components.xml | 41 | 0 | 0 | 0 |

One TypeScript/Vite production-build invocation passed. SQLite completed in 366.02 seconds; PostgreSQL in 794.21 seconds. Those timings were measured while browser/regression processes ran concurrently, not as standalone performance benchmarks. Each browser run's timing is retained in its sequence summary.

No new failures occurred in these twenty browser invocations or the additional regressions. The earlier v2 browser failure remains reported and preserved; original trace hashes were rechecked after validation. No claim is made that the baseline reproduced it or that ten passes prove the absence of every possible browser race.

Final disposition: **verified for the bounded synthetic demo**. Existing clinical-confirmation and production-readiness limitations remain. No live LLM calls, new dependencies, merges, pushes, rewritten history or tag changes.

