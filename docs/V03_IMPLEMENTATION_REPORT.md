# ReproBridge v0.3 implementation report

The release extends the existing five React routes. It retains FastAPI, PostgreSQL, the clinical rule versions, the authorization model, and the original evidence-verification gate.

| Change | Persisted source or behavior |
| --- | --- |
| Population counts and Amira entry | Patient, obligation, task, stage and audit records from the snapshot. Blocked or escalated counts distinct open obligations whose latest closure outcome was blocked or reopened. |
| Patient journey and dependencies | Patient stage, life-stage events, matched source Observation and stored typed dependency. Each endpoint links to its passport and provenance. |
| Obligation passport | Current obligation, rule, care owner, source, historical actions, completion records and verified state. Checkpoints summarize those fields independently of workflow order. |
| Resolution | Four real LangGraph node completions are persisted in the execution result in execution order. Older and failed runs show the trace availability accurately. Human review remains a separately authenticated action. |
| Evidence and interoperability | Persisted reviewer decisions, closure outcomes and supporting Observations. Downloads use the existing validated FHIR R4 endpoint. |
| Demo reset | A coordinator-only operation validates the canonical Amira fixture, archives that run’s dependent records, and restores the starting state in one serialized transaction. Audit history of unrelated patients stays untouched. The current-run snapshot exposes archive summaries only. |
| Technical evaluation | The checked-in readout is generated from a completed PostgreSQL test report and its verified browser downloads. Each row is a bounded regression or synthetic scenario result. |

Revision 0003 adds the archive table. The clinical data model and normal case actions continue to use the existing services. The prior audit history of the live installation was backed up before migrating.
