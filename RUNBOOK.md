# Ajyra AI - ReproBridge synthetic demo runbook

**Scope:** Synthetic data only. Timing policies and the historical finding remain pending clinical confirmation. Agents never decide timing, diagnosis, eligibility, relevance or closure. Wait for action confirmations before navigating.

## Start

Keep the existing provider key and role tokens in ignored `.env`. `OPENAI_MODEL` controls the original evidence agent; `EXPLANATION_MODEL` explicitly selects the model for the single-call explanation path. Match that variable to the model in the accepted replay files. Endpoint: `OPENAI_BASE_URL` (blank uses official OpenAI). No automatic model switch.

From the repository root in PowerShell:

```powershell
$env:DEMO_MODE='true'
$env:REPROBRIDGE_TEST_MODE='true' # Dedicated synthetic fixtures only
$env:CLINICAL_EVIDENCE_AGENT_ENABLED='true'
$env:LLM_MODE='replay'
# Explicitly select the model named by the shipped accepted recording.
$env:EXPLANATION_MODEL=(Get-Content backend/demo-replays/explanation-v1/tsp-demo-amira.json -Raw | ConvertFrom-Json).model
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another shell run `npm.cmd --prefix frontend run dev -- --host 127.0.0.1`. Open the printed local URL and sign in with the existing coordinator token. The branch/tag is not merged automatically.

## Reset and smoke

Run `.venv\Scripts\python.exe scripts/smoke_demo.py`. Its 60-second budget covers health/migrations, guarded synthetic reset, default date, Amira IN_WINDOW, uncertain-dating hold, live catalog reachability and explanation replay. It makes no generation request. Amira window/history must have accepted replay fields; the uncertain case may use the explicitly labelled rule fallback. The result details distinguish those outcomes.

For UI reset, expand Admin, choose Reset TSP demo, then Confirm reset TSP demo. Wait for completion and **2026-11-22**. Amira-only reset is separately nested and restores preconception. Reset demo date changes the session calendar only. A fresh profile starts on the default date.

## Demo order

1. Show dashboard urgency, then open Amira and the carried obligation/W1.
2. Contrast the uncertain-dating hold. No date is inferred for it.
3. Receive the clearly labelled simulated Hospital A source. Show the 2011 finding (age 16), provenance, current version and pending rule.
4. Explain computed window / earlier finding. The model returns fields in one no-tools call; the server validates every field and renders text. Replay mode appears inside Admin only.
5. If the agent declines or fails, show **Rule-generated explanation (agent abstained)** and expand Explanation trace. It is server rule output, not accepted agent text. Stale context suppresses fallback until reload.
6. Show evidence, clinician approval and explicit verified closure as separate gates. Explanation acceptance never closes care.

## Model or Wi-Fi failure

Select `LLM_MODE=live` or `replay` explicitly and restart. Successful-only capsules live in `backend/demo-replays/explanation-v1/`; source versions/digests, dates and policies must match. Missing/mismatching replay produces a labelled fallback, not a mock. Never weaken validation or hide an abstention.

To deliberately record two new live calls, use `scripts/record_explanations.py --output <new-directory>` after selecting live mode. It costs credits, refuses overwrite and saves only accepted fields. `--replay-check` verifies offline. Details: `docs/EXPLANATION_V1.md`. Never expose environment values or credentials in recordings.

## Release captures and replay reliability

From `frontend`, run `node capture-demo.mjs` against the explicitly replay-mode local server. It writes all five 1920×1080 screens and a scripted 90-second journey under `demo-assets/demo-v1/`. It requires the existing Playwright optional video binary (`npx.cmd playwright install ffmpeg`) and Edge; it adds no package dependency. The script authenticates in memory before opening a recorded page and writes no HAR or trace.

From the root, `scripts/repeat_journey.py --count 30 --label <unused-label>` runs sequential full journeys with isolated synthetic SQLite, no live generation and per-run reports. Ports 8013/5183 must be free; `REPROBRIDGE_E2E_API_PORT` and `REPROBRIDGE_E2E_WEB_PORT` select isolated ports explicitly. The separate `scripts/reliability_explanations.py` makes exactly 20 paid calls (ten per type) and must be run deliberately; it refuses to overwrite an existing live summary.
