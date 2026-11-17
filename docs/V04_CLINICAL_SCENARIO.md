# Amira Haddad’s illustrative scenario

Amira is a fabricated patient. Her preconception record contains a documented metabolic assessment requiring clinician reconciliation. The case illustrates a continuity problem. When pregnancy is registered while review is still outstanding, the receiving care team needs to see the earlier obligation and its evidence.

**Illustrative — Not Clinically Approved.** The observation is a workflow marker. It establishes no diagnosis, threshold, treatment recommendation, clinical risk or validated outcome. No external clinical guideline is asserted.

| Stage | Stored artifact | Meaning in the demo |
| --- | --- | --- |
| Preconception | Final `Observation/demo-initial-flag` with demo code `follow-up-flag` and value `outstanding` | Records that the assessment review is outstanding. Fresh fixtures add readable `CodeableConcept.text`. |
| Pregnancy registration | Final `Observation/demo-amira-pregnancy` and persisted stage event | Triggers the configured pregnancy handoff review. The original obligation ID and source remain traceable. |
| Handoff dependency | `requires_verified_closure` edge between two stored obligations | Verified closure of the linked pregnancy review depends on resolution of the preconception assessment. Pregnancy care can proceed. |
| Resolution | Final completion record, reviewer approval for its evidence, date and audit | The coordinator can verify closure only when the existing server checks pass. |

`preconception-follow-up@1.0.0` and `pregnancy-coordination@1.0.0` retain their persisted definitions, matching, closure codes and provenance. Narrative text is keyed by the configured rule and shown only for the canonical Amira source records. Other synthetic cases that use the generic rule retain their generic labels. [Clinical rule definitions](CLINICAL_RULES.md)

An existing v0.3 source can still be seeded again without a conflict. Reset recognizes the exact legacy fixture, archives the old run and creates the revised one. The original source is retained in the archive. A subsequent reset at the new starting state is a no-op.
