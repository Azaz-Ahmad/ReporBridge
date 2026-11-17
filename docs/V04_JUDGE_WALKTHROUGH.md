# Five-minute ReproBridge judge walkthrough

Open [the demo](http://127.0.0.1:5173/) with separately prepared coordinator and reviewer credentials. If rehearsing, use **Population dashboard → Reset Amira demo → Confirm reset** as coordinator. The preceding fixture run is archived. The initial case has one open assessment-review obligation.

| Time | Show | Speaking point |
| --- | --- | --- |
| 0:00–0:35 | Sign in as coordinator. From Population Intelligence select **Open Amira’s journey**. | Unresolved reproductive-care obligations can be hard to follow when care moves between pathways. |
| 0:35–1:15 | In the patient workspace read the documented metabolic assessment. Open **Preconception metabolic assessment review** and expand its provenance. | The passport records why review was required, who owns it, and what evidence is missing. The illustrative rule is unapproved and supplies no diagnosis. |
| 1:15–1:55 | Return to **Amira’s journey**. Register pregnancy. Show the timeline, the same assessment obligation and the linked **Pregnancy handoff review**. | The receiving team can see the prior obligation. The stored prerequisite applies to verified closure of the linked handoff review. |
| 1:55–2:45 | Open the assessment passport and **Open review queue**. Show the four configured steps and **Not started**. Run the agent. Sign in as reviewer and approve the proposal. | The actual graph collects evidence references, reconciles them, prepares a proposal and routes it. The human approval here is for obtaining evidence. |
| 2:45–3:25 | Return as coordinator, open the assessment passport and select **Verify closure**. Show the blocked reason. In **Evidence & audit** select the assessment and add verified synthetic evidence. | Starting or approving a coordination action leaves closure pending when evidence is missing. |
| 3:25–4:30 | Run coordination again and obtain approval as reviewer for the new evidence. Sign back in as coordinator and verify closure at the assessment passport. | Approval has to match the evidence that is now on file. Read the successful closure beside the earlier blocked attempts. |
| 4:30–5:00 | In **Evidence & audit** show the FHIR download and interoperability panel. | The bundle carries evidence, Task and Provenance. Future EMR adapters would let ReproBridge work alongside existing systems. |

Use the actual walkthrough screenshots in `docs/screenshots/v04` if live execution is unavailable. A recorded FHIR bundle from the verification report can accompany that fallback. Introduce the screenshots as a verified prior run.
