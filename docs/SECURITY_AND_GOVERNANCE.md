# Security and governance

Run on loopback with synthetic records. The ingestion boundary requires the synthetic tag and ID namespace. The submitting coordinator is responsible for using fabricated content.

The environment bootstrap generates three distinct tokens. The coordinator imports evidence, invokes the agent, and requests closure. The reviewer approves, rejects, or requests evidence. The viewer reads the demo workspace and exports. Authorization runs on the server, and the browser keeps the signed-in demo token in session storage until sign-out.

The workflow records state-changing operations and closure blocks with actor role, UTC timestamp, evidence references, applicable rule version, and outcome. Evidence remains immutable by identifier. Approval requires the reviewer to submit the evidence references shown at the time of review. The graph proposes administrative work through a review queue. There is no LLM, external messaging, or autonomous care authorization.

Demo tokens identify roles. Real deployments require individually authenticated users, least-privilege patient access, regulatory and clinical review, retention controls, and independent audit protection.
