# ReproBridge v0.4 implementation report

The application keeps its five routes, existing schema, coordinator and reviewer permissions, and clinical decision rules.

| Feature | Implementation |
| --- | --- |
| Synthetic clinical story | A metabolic-assessment label is persisted on new Amira observations. The scenario-scoped backend readout supplies plain-language labels, rationale, next action and completion evidence. The same wording is used in Amira’s proposed actions and exported FHIR Task. |
| Passport | Main view emphasizes the finding, owner, next step, requirements and current blocker. Identifiers, rule codes and source details are expandable. The visible blocker comes from the same read-only assessment used by the write gate, so viewing it creates no blocked event. |
| Resolution | Shows the four nodes configured in the backend before execution, selected-case context, and the role-permitted run action. After execution it displays persisted node trace, evidence, proposal, authorization context, timestamp and reviewer decision. Running is local request state. Failed and review-required outcomes come from recorded runs and tasks. |
| Clinical workflow | The existing transition and graph remain data-backed. The explanatory copy distinguishes closure prerequisites on the linked review from pregnancy care. The evidence screen separates a proposal decision, current closure check, last blocked result and verified closure. |
| FHIR and reset | The same R4 JSON Schema and patient-local reference validation run on export. Scoped reset supports both fixture versions and preserves archive separation. No EMR adapters are active. |

**Release decision: GO for the synthetic hackathon walkthrough.** See the [test report](V04_TEST_REPORT.md) and [remaining limitations](V04_REMAINING_LIMITATIONS.md).

Authorization and audit are server concerns outside LangGraph. The graph performs four deterministic steps. Human approval happens after routing. No external LLM or outbound tool is used.
