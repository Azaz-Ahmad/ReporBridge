# M08 remaining limitations

- Deployment and fixtures are synthetic. Roles are shared demo credentials. Production identity, patient enrollment, consent, source authentication and external adapters require separate work.
- The R4 check covers bundled structural validation and the bounded local-reference contract. Comprehensive profile, invariants and terminology validation remain unestablished.
- Document support is inline UTF-8 text and Markdown. OCR, PDFs and remote attachments are deferred. Cross-document links preserve source references. Version supersession follows the same logical resource ID.
- Missing evidence expresses limits of the available record. The same-time Observation conflict rule is an evidence signal, not a clinical determination. Normalization never invents codes or converts unsupported units.
- Freshness may be configured through the trusted tool binder with an approved reference. The shipped rules are illustrative, so the default retrieval has no clinical age cutoff.
- The local catalog is scoped and output is bounded. Large-scale source pagination, terminology services, arbitrary source version IDs and clinical document processing pipelines are deferred.
- The outbox exposes an authorized durable feed. A separate notification dispatcher and the identity ambiguity review UI are future work.
- Workflow corrections use conservative reopening and source disqualification. The M08 feed does not promote data into an existing closure rule. Retired workflow run versions are retained separately from current-run lookups.
