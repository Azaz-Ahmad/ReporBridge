# ReproBridge v0.4 UI review

Actual Playwright captures from the PostgreSQL walkthrough are stored in `docs/screenshots/v04`.

| Screenshot | Review |
| --- | --- |
| `01-population.png` | Amira entry, continuity statement and measured evaluation are visible. |
| `02-patient-workspace.png` | The pregnancy stage, assessment summary and retained obligation read together. |
| `03-obligation-passport.png` | The owner, current blocker and closure requirements are prominent. The expanded panel preserves rule and evidence identifiers. |
| `04-resolution-before.png` | The four configured steps, division of authority, selected case and permitted run action are visible before any execution. |
| `05-resolution-after.png` | The persisted trace and evidence appear with the proposal and reviewer actions. |
| `06-evidence-audit.png` | The proposal decision, verified closure and prior blocked reasons remain distinguishable. |
| `07-cross-pathway-dependencies.png` | Both persisted nodes, the observed registration event, type and closure-specific rationale are legible in the graph crop. |
| `08-mobile-workspace.png` | At 390 px the timeline, graph and clinical evidence remain readable. |

Browser review found long obligation labels could force the passport, resolution and audit views wider than the mobile viewport. Bounded selects and a shrinkable main grid resolved the issue. The final browser journey checked all five routes at 390 px. The screenshot helper starts full-page captures at the top so the sticky sidebar aligns with the page header.
