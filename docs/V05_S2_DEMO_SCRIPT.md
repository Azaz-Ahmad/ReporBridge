# Sprint 2 demonstration

## Existing demonstration

Open http://127.0.0.1:5173 and sign in with the existing local coordinator token. The five-screen workflow and Amira's current records remain available. The current patient is at pregnancy after the preserved prior demonstration.

Open Care-resolution center. The Clinical Evidence Investigation panel shows model configuration and provider status. The current local configuration displays the enabled Gemini provider and permits Run Investigation after synthetic-only confirmation. The deterministic care-resolution action remains usable.

## Configured OpenAI demonstration

Configure OPENAI_API_KEY, OPENAI_MODEL and CLINICAL_EVIDENCE_AGENT_ENABLED=true in the ignored local .env file and restart the backend. Keep all questions and sources synthetic.

Load the existing M08 synthetic dataset from the patient workspace if needed. Return to Care-resolution center, review the bounded question and confirm it contains synthetic demonstration data only. Select Run Investigation.

Inspect the actual persisted run, model, graph steps, chosen read tools, token usage, evidence sources, findings, missing information, conflicts and uncertainty. Open source citations for current normalized values and quality.

Select Submit for Human Review. Sign in with the reviewer token. Read the same packet and sources, enter a review note and choose Approve summary, Reject or Request evidence. The resulting summary decision is persisted independently.

The Clinical Obligation Passport still requires its evidence-specific reviewer approval and closure verification. Summary approval alone cannot satisfy that requirement.

## Verification commands

Run from F:\ReproBridge.

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_clinical_agent.py
.\scripts\Test-Demo.ps1 -PostgreSQL
.\.venv\Scripts\python.exe scripts/verify_clinical_agent_live.py
```

The first command uses deterministic test doubles. The last command requires configured OpenAI access and uses three disposable synthetic PostgreSQL schemas. Reports are saved under test-reports.
