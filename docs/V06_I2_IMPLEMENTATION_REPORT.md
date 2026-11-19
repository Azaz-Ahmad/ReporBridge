# Increment 2 implementation report

CONDITIONAL GO for the local synthetic multi-agent capability, subject to the limitations below. Three required final live investigations passed. No critical authorization, source-integrity, clinical-decision or closure safety defect remains in the exercised cases.

Starting commit: 630b8ddda5b436c4a57957828483a8c2f489c576. Ending commit is provided in the delivery message and git log -1.

Implemented a deterministic LangGraph supervisor around the preserved six-node A01 agent, plus genuine LLM-powered A02 Evidence Reconciliation, A03 Clinical Context and A04 Evidence Gap agents. Ten top-level nodes support selective routing, original-source context reuse, bounded execution, validated handoffs, final grounding, unified typed packets and human review. The original seven patient-scoped M08 tools are unchanged; specialist callable-tool allowlists are empty. Only trusted backend reads supply decision/prerequisite/timing context.

No database migration was needed. Existing 0005 run/review JSON persistence stores a versioned multi-agent envelope and immutable summary review; prevention migration 0006 and all five tables remain intact. One new POST endpoint /api/v1/agents/clinical-evidence/runs/multi-agent reuses existing status/list/get/trace/packet/submit/review endpoints. Clinical decision outcomes, policy mutation and closure remain separate authorized services with no AI write interface.

Care-Resolution Center now displays linked decision, objective, supervisor, actual specialist states, chronology/correction findings, exact prerequisite states, proposed clinician questions, source inventory, actual calls/usage/latency, unified packet, timing and reviewer controls. All five original screens and six innovation cards remain. Nine real screenshots under docs/screenshots/v06-i2 include initial/running states, each specialist, packet, actual synthetic review, decision integration and mobile layout.

The final matched live cases used 16 model calls / 11 tools versus single-agent 18 / 19. Total tokens decreased only 4.4% in this three-case sample; conflict-case latency and tokens worsened. No general optimization or clinical superiority is claimed. The separate full-dataset retained live run remains inspectable in the application with source correction lineage, conflict abstention and request_evidence summary review.

All baseline tests were preserved. The test report records final database, React, build, browser and FHIR checks, including 34 new backend safety/comparison checks and four new React checks. Tests use explicitly labeled doubles; live verification uses the real configured provider. Earlier real failures and harness corrections are disclosed in V06_I2_LIVE_MODEL_VERIFICATION.md.

Conditions: synthetic-only use, mandatory clinician review, illustrative timing/rules, bounded non-exhaustive context, synchronous non-resumable model execution, unavailable dollar-cost estimation and only three matched live samples. Keep the original single-agent workflow available and gather repeated evaluations before changing the default.
