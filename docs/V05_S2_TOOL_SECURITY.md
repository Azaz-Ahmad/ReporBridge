# Tool security review

The model receives seven thin adapters to the existing ClinicalTools methods.

| Tool | Existing request model | Permitted operation |
|---|---|---|
| get_patient_clinical_context | Filters | Evidence listing |
| search_patient_observations | Search | Structured Observation search |
| search_patient_encounters | Search | Structured Encounter search |
| search_patient_documents | Search | Untrusted document-section search |
| get_evidence_provenance | EvidenceId | Scoped source read |
| check_evidence_quality | EvidenceId | Scoped quality read |
| get_related_obligations | RelatedRequest | Existing obligation metadata read |

Patient identifiers, actor and role are excluded from tool argument schemas. Extra parameters fail validation. Result pages are capped at eight, argument JSON at 4000 characters and serialized tool output at 50000 characters. Provider output tokens and graph budgets bound the total investigation.

Each execution opens a short transaction, reauthorizes PatientAccess, verifies canonical synthetic Amira scope and exact identity ambiguity, and delegates to M08. Retrieved raw source resources must retain the synthetic tag before any corresponding evidence is sent to the provider. Missing documents expose unavailable metadata. No SQL, remote document fetch, clinical write, approval or closure tool is registered.

Tool traces retain name, call ID, parameter digest, outcome, retrieved IDs and elapsed time. Raw tool payloads and prompts remain ephemeral. Clinical question and bounded source excerpts in the review packet are retained because reviewers need to inspect the task and cited support. All run, trace, packet, list, source and review reads require authentication and patient authorization.

## API roles

Coordinator can create and submit investigations. Authenticated readers can view runs in their patient grants. Reviewer alone can record a summary review. Cross-scope run IDs return unavailable responses. Request replay and review replay are idempotent. A changed replay payload or conflicting immutable review returns 409.

Review records never enter clinical_approvals or closure_evidence. Existing deterministic closure checks continue to use their original evidence-specific approvals.

## Adversarial verification

Tests cover wrong-patient document IDs, extra patient parameters, forbidden write-tool names, revoked grants, ambiguous identity, fabricated IDs, mismatched values, instruction-bearing notes, provider errors and changed evidence. The synthetic injection test verifies tool and clinical-write boundaries using a test provider. Live model resistance remains unverified until live OpenAI evaluation is run.

No critical authorization or closure-boundary defect remained in executed tests. Shared demo roles and application-level grants remain prototype constraints.
