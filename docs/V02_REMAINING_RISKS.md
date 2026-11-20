# Ajyra AI - ReproBridge v0.2 remaining risks

- The two rule definitions are illustrative and have no clinical approval. The prototype must use synthetic records.
- Demo role tokens identify roles in one local synthetic workspace. Individual identities, per-patient access grants, a multi-tenant boundary, and audited production credential management are future work.
- Related evidence is append-only. The demo accepts a new invalidating record and reopens affected closures. Versioned FHIR corrections at the same resource ID and a human reconciliation UI for irreconcilable records are outside the supported contract.
- LangGraph uses deterministic evidence interpretation and fixed administrative templates. A partial run is discarded and can be retried. Durable graph checkpoints and live LLM or external messaging are unimplemented.
- PostgreSQL serializes demo write operations. The timings apply to a small local dataset. Production-scale concurrency and recovery objectives are unmeasured.
- The R4 check covers structural and bounded reference validation. Full profile and terminology conformance, regulatory assessment, and actual hospital connectivity are unestablished. Mother–child continuity remains an architectural extension.
