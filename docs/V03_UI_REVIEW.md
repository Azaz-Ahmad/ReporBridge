# Ajyra AI - ReproBridge v0.3 UI review

The five views use a navy sidebar, white and soft-gray surfaces, and teal and blue accents for actionable state. Text labels accompany every workflow status. The synthetic demonstration banner remains visible in the shared header. The passport labels illustrative rule definitions as unapproved beside their care requirements.

The screenshot set under `docs/screenshots/v03` comes from the real Playwright walkthrough with a freshly migrated PostgreSQL schema. The dashboard starts at preconception, the workspace and passport show the pregnancy transition, the resolution screen shows an authenticated human review, and the audit screen shows verified closure. The mobile image shows the patient workspace at 390 CSS pixels.

Visual review covers text wrapping, readable headings, spacing, keyboard-accessible native links and disclosures, and responsive treatment of tables and dependency diagrams. Visual inspection revealed cramped audit actor labels and narrow clinical evidence cells. The final layout keeps actor names intact, makes audit tables independently scrollable, and displays the clinical evidence as labeled rows on phones. The browser checks whole-page horizontal overflow across all five routes at mobile width.
