# Clinical rules

Both rules are illustrative demonstration rules created solely from the synthetic fixture specification in this document. Neither has clinical validation or approval for care use. The follow-up flags encode synthetic workflow state and carry no diagnostic or treatment meaning. No external clinical guideline is used.

## Preconception follow-up

`preconception-follow-up@1.0.0` applies during the preconception stage when a final demo-system Observation has code `follow-up-flag` and value `outstanding`. The coordination obligation preserves the source and assigned owner. Closure requires qualifying `follow-up-reconciled` evidence.

## Pregnancy coordination

`pregnancy-coordination@1.0.0` applies after synthetic registration. A final demo-system `pregnancy-registration` Observation with value `registered` supplies the source. An unresolved preconception obligation is carried forward and linked as a prerequisite. Closure requires qualifying `pregnancy-handoff-reconciled` evidence and closure of the linked preconception obligation.

## Decision gates

Missing, conflicting, or nonfinal trigger records cause the applicable rule to abstain and log the evidence considered. Completion records must be final, unambiguous, and carry `verified`. A reviewer must approve the exact current completion evidence references. The coordinator requests closure, and the service checks evidence, prerequisites, and approval in one transaction. A blocked attempt leaves the obligation open and records the reason.
