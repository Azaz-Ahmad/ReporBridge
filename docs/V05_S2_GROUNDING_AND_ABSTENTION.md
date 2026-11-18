# Grounding and abstention

The strict Draft contains summary, findings, missing information, conflicts, uncertainty, review actions, abstention and scope. Each finding includes a statement, supporting IDs and source versions, an exact excerpt or structured value, evidence status and interpretation flag. Backend-owned run ID, patient ID, model, timestamps and source references are added only after validation.

## Deterministic checks

Every cited ID must have been retrieved through an authorized M08 tool. Its current patient, version, digest and quality must match the retrieved snapshot. The complete catalog fingerprint must remain stable. Model-supplied excerpts must appear in the returned document sections. Structured JSON values must match the specific normalized.values key, including JSON type.

Unavailable evidence cannot support a clinical finding. Superseded sources must be marked historical. Conflicting retrieved observations require explicit conflict acknowledgement and abstention. Unknown IDs, altered values, unsupported versions, missing citations and changed snapshots fail grounding.

Statements beyond an exact source quotation or exact structured value are marked as requiring clinical interpretation. A narrow lexical screen also rejects explicit generated diagnostic, prescribing, dose-change and clinical-verification language. The screen has false-positive and false-negative limitations.

Free narrative summaries, missing-information claims and recommended review actions receive mandatory human review. Citation existence establishes source provenance. Semantic entailment of every narrative claim remains unverified.

## Statuses

- partially_grounded for checked sources and values with narrative requiring review.
- insufficient_evidence for inaccessible or insufficient records, provider/tool failures, budgets or outside-scope questions.
- conflicting_evidence for acknowledged unresolved source conflicts.
- validation_failed for rejected grounding or evidence-integrity checks.
- source_references_validated is reserved in the contract. Current free-narrative packets receive partially_grounded at best.

A rejected draft is withheld. A clearly labeled system_abstention packet provides the error and safe review route. It never appears as successful model generation. Supported conflict packets may preserve model findings while abstaining from a clinical conclusion.

ClinicalEvidenceReviewPacket always requires_human_review. Review submission revalidates the snapshot. Approving a summary records an evidence-review decision in its own table. Existing closure authorization remains independently required.

## Boundaries

The agent investigates documented evidence. It cannot determine that care never occurred from an unsuccessful search. Canonical synthetic Amira, explicit synthetic-question attestation, source tags and exact identity checks limit outbound data. This sprint does not provide real-patient consent, production identity verification, clinical diagnostic validation or automated semantic proof.
