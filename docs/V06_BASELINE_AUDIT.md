# v0.6 baseline audit

Verified in F:\ReproBridge at commit 1a12155f2727aef9fbcd87fad8ff7a7e34f46b1e with a clean worktree. No repository AGENTS.md was found.

The application has five React screens, a deterministic care-resolution graph, and one six-node Clinical Evidence Agent using the configured Gemini/OpenRouter Responses integration. All seven M08 tools enforce backend patient scope. M08 provides immutable source versions, corrections, document sections, quality flags and provenance. Reviewer tokens are distinct from coordinator/viewer tokens. Evidence-specific clinical approvals govern obligation closure.

Migration head is 0005. Amira reset archives the canonical clinical workflow and preserves unrelated patients and the independent M08 feed. New decision history must survive reset and avoid foreign keys to deleted historical workflow rows.

No approved clinical timing policy exists. The default prevention decision will have no deadline. Any timing demonstration will use separately labeled illustrative policies and fixtures.

Baseline command scripts/Test-Demo.ps1 -PostgreSQL completed successfully before implementation. Reports are in test-reports/20261119-204245-00c6db9e.

- 93 Python tests passed on PostgreSQL.
- 93 Python tests passed on supplementary SQLite.
- 12 React tests passed.
- TypeScript/Vite build passed.
- Both PostgreSQL browser journeys passed.
- Both FHIR downloads validated.

The implementation adds a separate persisted decision lifecycle, immutable reviewer records, prerequisite registry, timing policies and decision audit. It reuses M08 retrieval and the existing agent, role dependencies and transaction serialization. The existing six innovations and all five screen entry points are retained.
