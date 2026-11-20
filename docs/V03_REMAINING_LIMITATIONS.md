# Ajyra AI - ReproBridge v0.3 remaining limitations

- The two illustrative rule definitions are unapproved. Use fabricated data. Clinical effectiveness and patient outcomes have not been established.
- The local demo uses shared role credentials. Individual identity, per-patient grants, and production audit protection remain future work.
- LangGraph evaluates supplied records deterministically and prepares administrative proposals. The prototype records successful node completion and failed run outcomes. Incomplete and older v0.2 traces lack per-node history. External LLM, external tools, and messaging are unconfigured.
- The supported transition is preconception to pregnancy. Postpartum and mother–child continuity are planned.
- FHIR R4 validation covers the JSON schema and the supported local-reference contract. Full profile, terminology, and EMR integration validation remain future work.
- Reset is restricted to the canonical Amira fixture. A nonfixture import or cross-patient dependency requires a separate rehearsal database. The UI displays archive summaries. Detailed archived records are retained in PostgreSQL without a restore UI.
- The technical evaluation uses a small labeled synthetic fixture set. It establishes behavior on those cases and cannot support clinical performance claims.
