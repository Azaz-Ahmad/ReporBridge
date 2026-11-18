# Sprint 2 test report

This records the initial Sprint 2 regression run. Current 93-test database suites and live Gemini release gates are recorded in V05_S2_GEMINI_VERIFICATION.md.

The final complete command was `scripts\Test-Demo.ps1 -PostgreSQL`, executed on 18 November 2026.

Artifacts are in `test-reports/20261118-230629-1dd024a9`.

| Verification | Actual result |
|---|---|
| Python on PostgreSQL | 81 passed |
| Python on supplementary SQLite | 81 passed |
| React components | 12 passed |
| TypeScript and Vite production build | Passed |
| Fresh PostgreSQL browser journey | 1 passed |
| Independent PostgreSQL browser replay | 1 passed |
| Downloaded FHIR R4 bundles | Both passed bundled structure and patient-local reference checks |

All 53 Sprint 1 Python tests were retained. The new investigation suite adds 28 checks, including 16 labeled scenario records, all seven real tool implementations, authorization, concurrent replay, review separation, stale evidence and official SDK wire/error behavior. Three new component tests cover unavailable-provider state, run endpoint submission and persisted findings, and visible backend failure.

The PostgreSQL test fixtures create disposable schemas. Browser runs also use separate schemas and random role tokens. They exercise all five existing screens, pregnancy transition, obligation dependencies, deterministic LangGraph, evidence-specific review and closure, audit, FHIR export, M08 explorer and demo reset. The browser now additionally verifies the real disabled-provider investigation panel. Its test configuration explicitly disables paid OpenAI requests.

The standalone command `.venv\Scripts\python.exe scripts/evaluate_clinical_agent.py` passed 28 tests and saved 16 labeled records in `test-reports/agent-eval-20261118-230616-d99d2db1`. SDK MockTransport tests validate Responses request shape, function/draft parsing, usage extraction, retry limits, timeout, authentication, malformed output and incomplete responses without network access.

Live verification command `.venv\Scripts\python.exe scripts/verify_clinical_agent_live.py` recorded BLOCKED in `test-reports/openai-live-20261118-225530/summary.json`. No API key was configured. Actual successful OpenAI runs total zero.

## Live upgrade and visual checks

The pre-upgrade PostgreSQL dump and summary are in `test-reports/sprint2-upgrade-8a71eb99e6`. Migration 0005 applied successfully. All 20 existing workflow and M08 tables matched their before/after row counts and content hashes. Amira's stage remained pregnancy.

After backend restart, /api/health returned 200. The authenticated investigation status endpoint returned disabled. Desktop and 390-pixel screenshots were captured and inspected. Encoding artifacts and checkbox alignment found during visual QA were corrected. The corrected panel fits the mobile viewport.

## Remaining verification

The automated model tests use explicitly labeled test doubles. Three real complete/missing/conflicting OpenAI investigations remain required for an unconditional LLM release decision. Model selection quality, narrative detection quality, live latency and actual token usage remain unmeasured.

The current release decision is CONDITIONAL GO.
