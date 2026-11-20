# Ajyra AI - ReproBridge — demo-v1 release notes

**Release decision: GO for the local synthetic replay demo.** All mandatory gates below passed. Synthetic demonstration only. Policies and the historical finding are **pending clinical confirmation**. This release does not authorize clinical use.

## What works

* Consistent product naming and human-readable main-screen labels. Exact source identifiers, rule versions and hashes remain available in explicit technical details; stored contracts and grounding inputs are unchanged.
* The 2011 Hospital A source is shown at age 16, received through a clearly labelled SIMULATED exchange. Pregnancy dates and the 2026-11-22 demo clock are unchanged. Earlier records, existing W1 timing, evidence, reviewer approval and verified closure remain distinct.
* TSP/history explanations use the existing single no-tools structured call and original grounding checks. The model copies server-prepared fields; the server compares them exactly and renders text. It never delegates window, eligibility, relevance or closure decisions to an agent. Failures retain a visible, labelled rule-generated fallback.
* Exact-source replay now covers both the original history version and a freshly seeded version. A mismatching date/version/hash/schema still abstains. Fresh-clone keyless replay accepted both explanation types with zero live calls, tokens and tools.
* No M08 contract, patient grant, seven-tool authorization, six-node workflow, clinical approval gate, timing rule or closure rule was changed. No package dependency or database migration was added.

## Live reliability: twenty real authenticated requests

The configured explanation model was retained: requested `anthropic/claude-sonnet-5.5-20260928`, reported `anthropic/claude-sonnet-5.5`, through OpenRouter. Every trace contains one real response ID, one model call, zero tools, zero retries and complete usage. No alternate model or mock was used.

| Explanation | Accepted | Latency min / mean / max | Total input / output tokens | Guard rejections |
|---|---:|---|---:|---:|
| TSP window | 10/10 | 6.390 / 8.129 / 10.367 s | 26,670 / 6,550 | 0 |
| Historical finding | 10/10 | 10.396 / 11.178 / 12.985 s | 31,190 / 10,910 | 0 |

All twenty remain `partially_grounded`, with no field mismatches or validation errors and mandatory human review. This is exact-field reliability, not clinical correctness certification or an SLA. Full scrubbed traces and persisted SQLite runs are in `test-reports/release/live/`; safe per-trial metrics are in `demo-assets/demo-v1/live-reliability.json`.

Original investigations remain configured with `google/gemini-3.8-flash-20260902`. This release did not repeat their paid calls. The inherited complete/missing/conflicting live proof was checked in `test-reports/openai-live-20261118-235154-39baee/summary.json`: all three passed every recorded citation, structured-value, tool-execution, abstention, human-routing and unchanged-clinical-state check. These are inherited observations, not new live runs.

## Regression evidence — exact invocations

The final full fresh-clone backend suites include the added shipped-capsule integrity test. The original full suites ran before that test was added; it also passed independently there.

| Location / report | Executed entries | Passed | Failed | Collection errors | Skipped |
|---|---:|---:|---:|---:|---:|
| original / `capsule.xml` | 1 | 1 | 0 | 0 | 0 |
| original / `postgres.xml` | 272 | 272 | 0 | 0 | 0 |
| original / `react-audit-retry.xml` | 48 | 47 | 1 | 0 | 0 |
| original / `react-audit.xml` | 48 | 46 | 2 | 0 | 0 |
| original / `react-date-label-retry.xml` | 53 | 53 | 0 | 0 | 0 |
| original / `react-date-label.xml` | 53 | 52 | 1 | 0 | 0 |
| original / `react-final-audit.xml` | 52 | 52 | 0 | 0 | 0 |
| original / `react-reviewer-audit.xml` | 52 | 52 | 0 | 0 | 0 |
| original / `sqlite-retry.xml` | 272 | 272 | 0 | 0 | 0 |
| original / `sqlite.xml` | 13 | 0 | 0 | 13 | 0 |
| fresh clone / `postgres.xml` | 273 | 273 | 0 | 0 | 0 |
| fresh clone / `react-final.xml` | 53 | 53 | 0 | 0 | 0 |
| fresh clone / `react-frozen.xml` | 52 | 52 | 0 | 0 | 0 |
| fresh clone / `react.xml` | 52 | 52 | 0 | 0 | 0 |
| fresh clone / `sqlite.xml` | 273 | 273 | 0 | 0 | 0 |

`sqlite.xml` in the original checkout records **zero executed tests and thirteen collection errors** from invoking pytest at the repository root without its backend import path. The corrected backend-directory invocation passed 272 tests. The initial React failures were outdated identifier/citation label expectations and an encoding/import edit; corrected results are shown separately, never substituted for the failures. The two release-artifact redaction tests passed in each checkout. Final original and fresh-clone TypeScript/Vite builds passed. The later date-label test initially used an exact DOM matcher that omitted adjacent EDD text (52 passed, 1 failed); its corrected exact-prefix check passed in the full 53-test suite in both checkouts. The label now correctly describes a dating value rather than a record timestamp; all values and calculations are unchanged.

**Final frozen browser sequence: 30/30 consecutive full journeys passed; zero skips, retries or flaky results.** The application stayed unchanged at `9f097d8` throughout these thirty runs. They use the real local backend with the existing explicit disabled-agent test setting, not thirty live model calls. Actual live explanations and accepted keyless UI replay are verified separately above.

| Browser group | Invocations | Passed tests | Failed tests | Startup failures (zero tests) |
|---|---:|---:|---:|---:|
| Initial UI-selector attempts | 3 | 0 | 3 | 0 |
| Corrected UI selectors | 1 | 1 | 0 | 0 |
| Earlier batch: interrupted for reviewer audit | 7 | 7 | 0 | 0 |
| Earlier batch: interrupted for date-label audit | 22 | 20 | 0 | 2 |
| Fresh-clone journeys | 3 | 3 | 0 | 0 |
| Final frozen application: thirty consecutive | 30 | 30 | 0 | 0 |

The initial three browser failures were selectors tied to identifiers moved out of visible labels. Their corrected selectors still assert the exact FHIR source inside provenance, and the patient-isolation check additionally asserts an empty clinical evidence table for the other patient. The two startup failures were port 8013 still occupied by the previous interrupted invocation; no test ran in either. The final independent sequence uses ports 8033/5233 and fresh SQLite per invocation. Earlier batches were deliberately interrupted for presentation corrections; orphaned completed invocations are included from their actual JSON reports, not silently discarded.

All initial React/collection/browser failures, raw unsuccessful recording attempts and redacted capture diagnostics remain under ignored `test-reports/release/`. Capture failures included a role-bootstrap error, an unsupported VP8 export option, a history-receipt assertion (exact message unavailable in that early attempt), and an isolated server not yet ready (`ECONNREFUSED`). The corrected final native-VP9 capture passed all assertions. Ephemeral credentials were removed while retaining failure steps, source evidence and screenshots. Public count-only evidence is in `demo-assets/demo-v1/verification.json`; detailed local reports remain available in both checkouts.

## Fresh-clone QA and portability

A real independent clone was created at `F:\ReproBridge-demo-v1-qa`, with a newly created virtual environment and `npm ci`; no original node_modules, virtualenv, database or ignored replay artifacts were copied. Declared Python dependencies were installed from `backend/requirements.txt` and their actual versions retained in `test-reports/release/python-installed.txt`. Backend tests used clone-local `--basetemp` directories. PostgreSQL cases used isolated per-test schemas on the existing local PostgreSQL service.

The clone was migrated through 0009, initialized with fresh role tokens, seeded/reset through the guarded local API, and passed the 12/12 smoke in **12,625 ms**. The catalog check used the existing provider key in the child process only; no key was stored in the clone. A subsequent server restart with an empty provider key accepted **2/2** replay explanations, zero live calls/tokens/tools. The committed video was then captured against this keyless fresh-clone SQLite server.

This is a fresh folder on the same Windows host, not a new-machine or Linux certification. Python, Node/npm, Edge (or explicitly configured Playwright browser), and a reachable PostgreSQL service are prerequisites. Role tokens, database credentials and live provider credentials must be configured locally. Python dependency version ranges and external provider availability remain operational limits. Internet is needed for installation, the optional Google font and live provider calls; the UI has a sans-serif font fallback and accepted replay requires no provider key or inference connection.

## Captures and repeatable commands

`demo-assets/demo-v1/` contains all five screens plus five journey snapshots, each exactly **1920×1080**, and **journey-replay-90s.webm**: native VP9, 25 fps, verified **90.00 seconds**. The scene manifest records the actual timings; clinician approval and explicit closure finish before the cut. Authentication is set before opening a recorded page, with no login frames, HAR or trace. Only synthetic UI is captured.

Run the existing API/frontend first, explicitly in replay mode. From `frontend`, run `node capture-demo.mjs`. Optional `CAPTURE_URL` and `CAPTURE_ENV_FILE` select a local isolated demo. Install the existing Playwright optional video runtime with `npx.cmd playwright install ffmpeg`; no package was added. The recorder refuses live mode and requires accepted zero-live-call replay responses.

From the root, `python scripts/repeat_journey.py --count 30 --label <unused-label>` runs full sequential journeys with isolated SQLite and per-invocation reports. Keep ports 8013/5183 free, or explicitly set `REPROBRIDGE_E2E_API_PORT` / `REPROBRIDGE_E2E_WEB_PORT`. `python scripts/reliability_explanations.py` deliberately spends credits on exactly ten calls per type and refuses to overwrite an existing summary. Never run it as an automatic demo fallback.

## Known limits

* Timing policies, the PCOS seed placeholder and historical-finding link await clinical confirmation; this is no clinical risk, diagnosis or treatment decision service.
* No live institutional exchange, real patient data, production identity/consent system, mother–child workflow or production deployment is claimed.
* Replay is exact-context coverage, not general offline inference. Uncertain dating remains on hold and may display the labelled rule fallback. Source/date/policy changes may correctly cause abstention.
* Explanation acceptance, summary review, clinician approval and evidence-verified closure are separate. All existing safety gates remain active.
* Initial UI panels load asynchronously; captures wait for actual patient/window data. Wait for completed mutation responses and confirmations before navigating. The original global write lock can cause contention under parallel regression load.

See DISCLOSURE.md for the earlier `de5e9d3` baseline, actual tag chronology, AI development tooling and runtime model disclosures. Release is on `release/demo-v1`; no merge, push, force-push or history rewrite is performed. The final main-app smoke passed 12/12 in **24,813 ms**, with zero paid requests; the app is running in explicit replay mode on the default 2026-11-22 date. Freeze identifier: annotated local tag **demo-v1**. No merge or push is authorized or performed. The fresh-clone tested application is byte-identical to the frozen release application; later commits contain release evidence, captures and documentation only.
