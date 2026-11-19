# Decision-readiness agent integration

Decision readiness reuses the existing Clinical Evidence Agent, current Gemini/OpenRouter Responses configuration and all seven M08 tools. It introduces no additional model agent or graph node.

The six nodes remain validate_request, investigate, authorized_tools, validate_grounding, prepare_review_packet and human_review_queue.

## Trusted binding

A coordinator sends a decision ID in the endpoint path and a bounded request ID. The backend authorizes the linked patient, reevaluates prerequisites, builds the clinical question and binds the investigation to decision ID, patient, source snapshot hash and revision.

Run persistence includes decision_context. The model receives the decision/obligation context but cannot choose the authenticated patient or role. Clinical tools still receive PatientAccess from the backend. Model choices remain limited to the same seven read tools.

The replay fingerprint includes trusted decision context. A repeated request returns the original run, while changed decision context under the same request ID fails with a conflict. Concurrent in-flight repeats do not prematurely finalize a run.

## Grounding and clinical boundaries

The existing checks validate source IDs, versions, values, excerpts, patient scope, conflicts and current evidence. Decision grounding additionally checks that the trusted decision context remains current and rejects explicit generated timing advice. The backend timing engine never consumes LLM output.

The model cannot write a prerequisite, timing policy, decision outcome, approval or closure. Technical prerequisite state is computed by the gateway evaluator. Clinical decisions use the reviewer-only endpoint and current snapshot attestation.

The completed readiness packet is linked to the decision, its actual retrieval is audited and it is submitted to the existing human-review queue when the binding remains current. General and decision-bound investigations use separate frontend lists. Source citations open the existing scoped M08 evidence endpoint.

## Actual live verification

The first real bound run was safely rejected with unknown_citation and conflict_not_acknowledged. Its system-abstention packet and trace remain persisted. The prompt was clarified to distinguish tool item.id from decision/obligation/FHIR identifiers and to require conflict abstention.

The subsequent genuine run succeeded with conflicting_evidence, explicit abstention and pending_review. It used six real model calls and five authorized tool executions. Usage was 35,316 input and 2,466 output tokens with zero retries. The application clinical snapshot was identical before and after the investigation.

The requested model was google/gemini-3.8-flash-20260902. OpenRouter reported google/gemini-3.8-flash. Both identifiers and response IDs are retained.

Proof is in test-reports/v06-live-ae36a7bdc0/summary.json. The persisted run ID is investigation-4be08f8029e44cc5a211917843e365ff. The rejected earlier attempt is in test-reports/v06-live-50b687bb37/summary.json.

This verifies the readiness integration with real provider calls. Unit/integration tests using test doubles remain explicitly distinct.
