# Remaining limitations

This is a local synthetic prototype. It uses the canonical Amira patient only; no real patient information is sent. Demo role tokens are not production staff identity. Clinical rules and decision timing remain illustrative and require appropriate clinical governance.

Specialists have no independent retrieval tools. A01's bounded inventory can miss relevant records; truncation is disclosed and clinical completeness is never claimed. A valid citation verifies ownership/version/excerpt/value, not semantic truth. Narrative context, review questions and discrepancy explanations remain interpretations for clinician review. Clinical conflict resolution requires human authority.

The supervisor is synchronous with persisted node checkpoints. It does not resume an interrupted model call or supply distributed durable execution. Polling shows actual saved states; in-flight provider calls retain their configured timeout after a workflow deadline is crossed. There is no dollar-price catalog or enforced currency ceiling. Context character limits are approximate token controls.

No automatic expensive-model escalation, model fallback, clinical action or obligation closure exists. Comparative performance and any observed failures are reported in the evaluation/live reports. Additional agents may cost more or be slower even when input context is smaller. Approval of a packet is summary review only; clinical decision recording and closure remain separate authorized workflows.

The final matched live sample reduced aggregate total tokens by only 4.4%; the conflict case was slower and consumed more. Earlier actual runs failed safely for output truncation and grounding, as recorded in the live verification report. Interrupted experimental batches preserve completed cases only; in-flight provider billing cannot be reconstructed from those partial summaries. These are additional reasons to retain the single-agent option and avoid a generalized performance claim.
