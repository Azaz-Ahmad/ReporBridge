# ReproBridge judge walkthrough

Allow about five minutes. Open [the local demo](http://127.0.0.1:5173/) and have the separately issued coordinator and reviewer credentials available locally. Use the browser’s sign-out control when switching roles.

| Time | Action | What to point out |
| --- | --- | --- |
| 0:00–0:40 | Sign in as coordinator. In Population Intelligence select **Open Amira’s journey**. If the case is absent, choose **Load demo patient** first. | ReproBridge keeps an unresolved care obligation visible when the patient moves between pathways. The dashboard counts come from persisted records. |
| 0:40–1:25 | Open **Preconception follow up**. Expand **Source evidence and provenance**. Return via **Amira’s journey**, select **Register pregnancy**, then open the same obligation. | Show the current stage, retained obligation ID, illustrative rule and source Observation. The dependency map links the persisted pregnancy event and the two obligations. |
| 1:25–2:15 | Select **Run care-resolution agent**, then **Open review queue**. Switch to reviewer and approve the proposal. | Point to the four recorded LangGraph nodes, the evidence references and the proposed action. This approval is for obtaining evidence. |
| 2:15–3:05 | Switch to coordinator. Return to the passport and select **Verify closure**. Open **Evidence & audit**, select the preconception obligation under submission and choose **Add verified evidence**. | The first attempt is blocked and audited. Adding evidence still requires a new evidence-specific review. |
| 3:05–4:15 | Run the agent again from the passport, open the review queue, switch to reviewer and approve the new proposal. Switch back to coordinator and verify closure from the preconception passport. | Show the evidence-available result, reviewer authority and the verified closure state. |
| 4:15–5:00 | In **Evidence & audit**, show the blocked and verified outcomes and select **Download FHIR bundle** for Amira. | The bundle carries observations, Task and Provenance. Discuss future EMR adapters and the planned mother–child relationship using the **Six innovations** panel. |

## Rehearsal reset

As coordinator, open **Population dashboard**, expand **Reset Amira demo**, then choose **Confirm reset**. The backend restores one open preconception obligation and puts the previous fixture run’s records and audit in a separate archive. A second reset at the initial state is a no-op. See **Archived Amira demo runs** in **Evidence & audit** for summaries. The reset refuses a fixture with unrelated imports or cross-patient dependencies. If it refuses, use a disposable migrated PostgreSQL schema for rehearsal.

## Backup procedure

Use the Playwright screenshots in `docs/screenshots/v03` in numbered order if the live demo becomes unavailable. They show a completed synthetic run. A downloaded and independently validated Amira bundle is available in the local verification report directory referenced in the [test report](V03_TEST_REPORT.md). Use the screenshots and bundle to explain the actual tested flow, and distinguish the fallback from a live execution.
