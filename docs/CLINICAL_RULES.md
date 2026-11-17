# Clinical rules

Both rules are illustrative demonstration rules created solely from the synthetic fixture specification in this document. They have no clinical approval. Follow-up flags encode synthetic coordination state. No external clinical guideline is used.

The v0.4 Amira fixture uses a readable preconception metabolic-assessment label. This narrative does not alter the decision definitions, source codes, matching or closure criteria. See the [v0.4 scenario](V04_CLINICAL_SCENARIO.md).

## Preconception follow-up

`preconception-follow-up@1.0.0` applies during preconception when a final demo-system Observation has code `follow-up-flag` and value `outstanding`. The obligation preserves its source and owner. Closure requires qualifying `follow-up-reconciled` evidence.

## Pregnancy coordination

`pregnancy-coordination@1.0.0` applies after synthetic registration. A final demo-system `pregnancy-registration` Observation with value `registered` supplies the source. A preconception obligation is retained as a `requires_verified_closure` dependency when it exists. Closure requires qualifying `pregnancy-handoff-reconciled` evidence and verified closure of the linked prerequisite.

## Decision gates

Missing, conflicting, or nonfinal trigger records cause the evaluator to abstain. Evaluation refuses a reused rule version with a changed definition. Completion observations must be final and carry the exact synthetic value `verified`. Only a reviewer approval of a current evidence-verification proposal can authorize closure. The service checks evidence, dependencies, and authorization in one transaction.

New completion evidence or an invalidating source record reopens affected obligations and closed dependents for reconciliation. Earlier approvals and closure evidence remain in history. A subsequent closure requires fresh review.
