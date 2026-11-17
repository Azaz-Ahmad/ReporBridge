# ReproBridge v0.2 security review

The local synthetic demo uses random coordinator, reviewer, and viewer bearer tokens from the ignored root environment file. The server rejects missing, invalid, and ambiguous credentials. The browser ships no token and stores a manually entered token in session storage. Tokens are cleared on sign-out.

| Role | Accepted operations |
| --- | --- |
| Coordinator | Read, import synthetic evidence, register pregnancy, run coordination, and request closure |
| Reviewer | Read and approve, reject, or request additional evidence for a pending proposal |
| Viewer | Read synthetic state and export patient bundles |

An approval is bound to the task, its graph execution, the obligation, and its evidence snapshot. A missing-evidence or conflicting-evidence proposal grants no authority to close. The service checks actual persisted observations for patient, configured code system and code, exact synthetic value, valid status, ambiguity, and applicable prerequisites. Late evidence that changes a previously verified basis reopens the obligation. Reopened cases require a fresh review. Completion and its audit are atomic.

Roles share the synthetic workspace. Evidence selection, references, closure, and export are patient-scoped. Audit identifies the acting demo role and UTC timestamp. Individual identities, patient-level grants within the shared workspace, hardened secret storage and external tamper-evident audit remain production work. Operate on loopback with fabricated data. The synthetic tag is a submitter assertion.
