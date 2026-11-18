# Sprint 2 baseline audit

Verified 18 November 2026 in F:\ReproBridge at 737f7ceb4bd81a5b137dbbfaf3801e4b47ff6cc7. Git worktree clean. No AGENTS.md found at repository or drive root.

FastAPI main.py authenticates bearer role tokens and enforces coordinator/reviewer separation. M08 PatientAccess and grants enforce patient scope. Existing deterministic LangGraph retrieve/reconcile/prepare/route uses local evidence and remains independent.

ClinicalTools exposes all seven requested methods. Filters, Search, EvidenceId and RelatedRequest reject extra fields. ClinicalRetrieval checks patient-local references, content hashes, source versions, historical status, normalized values, document excerpts and quality. The evidence registry, receipts, outbox and corrections are immutable/versioned. Existing Care-resolution Center displays deterministic proposals and evidence-specific closure approval.

Baseline command `scripts\Test-Demo.ps1 -PostgreSQL` completed successfully before implementation. Reports in `test-reports/20261118-224018-634e1263`.

- 53 Python tests on PostgreSQL.
- 53 Python tests on supplementary SQLite.
- 9 React tests.
- Production TypeScript/Vite build.
- Two fresh PostgreSQL Playwright journeys, both exports independently checked against bundled R4 structure and local references.

Official OpenAI SDK was absent and is now installed as 2.54.0. Its Responses.create interface supports store=False, function tools and structured output. OPENAI_API_KEY presence check returned false without exposing credentials. Live OpenAI verification is blocked pending configuration.

Implementation will add separate run/review persistence and a bounded model/tool graph. Existing rule definitions, closure approvals and deterministic graph retain their entry points.
