# Evidence registry and correction ledger

Alembic revision `0004` adds seven tables.

| Table | Purpose |
| --- | --- |
| `clinical_patient_grants` | Explicit patient and demo role scope |
| `clinical_identity_claims` | Exact external namespace claims and attribution |
| `clinical_evidence_versions` | Immutable source payload, patient, version, normalized data, SHA-256 and predecessor |
| `clinical_document_chunks` | Indexed document sections referencing an evidence version |
| `clinical_event_receipts` | Patient-scoped source event IDs, fingerprints, timestamps and evidence links |
| `clinical_change_outbox` | Durable sequence of accepted changes and affected workflow obligations |
| `clinical_access_audit` | Authorized reads, scope denials and identity claim activity |

Existing workflow evidence has equivalent immutable storage with auditable receipt and run scope. The provider projects it under stable per-run evidence IDs. Workflow correction materializes the original before adding the next version. The source record and previously verified workflow audit retain their integrity. Reset separates workflow run scopes. Independently imported clinical evidence remains available.

Exact events replay to the same evidence ID. Reusing an event ID or version with conflicting contents produces HTTP 409. Version gaps and regressing source event timestamps fail within the transaction. An accepted next version links to the prior version and appends one outbox notice. An invalidation withholds current content, supersedes pending affected workflow proposals and invokes the existing reopening cascade. The legacy gate treats changed observations as unqualified until reconciliation through the workflow. No event closes an obligation.
