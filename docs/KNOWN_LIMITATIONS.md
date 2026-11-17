# Known limitations

- The rules describe synthetic coordination flags and have no clinical approval. The synthetic tag is a submitter assertion and cannot independently detect real patient data.
- The fixed roles share a small synthetic workspace. Role tokens do not establish individual identity or support patient-level access controls.
- Administrative proposals stay in the demo queue. The graph runs synchronously and uses deterministic nodes.
- The FHIR boundary validates the supported resource shapes and demo rules. Full terminology, profile conformance and external reference resolution are future work.
- Evidence is append-only. A new invalidating observation can reopen an obligation. Same-ID FHIR updates and a governed reconciliation workflow remain future work. Use a fresh demonstration database or the automated PostgreSQL replay for another run.
- The database audit is transactionally persisted. Tamper-evident external storage, retention policies, production authentication, and deployment are future work.
- The demo shows one journey and two configured rules at version 1.0.0. Mother–child continuity and hospital integrations are architectural extensions.
