# ReproBridge synthetic demo runbook

**Scope:** Synthetic data only. Timing policy and the historical finding remain pending clinical confirmation. No live hospital exchange. Agents cannot decide timing, diagnosis, eligibility or closure. Wait for each action's confirmation before navigating.

## Start

Keep the provider key and existing role tokens in the ignored root `.env`. Set `OPENAI_MODEL` to an exact model allowed by your key; `OPENAI_BASE_URL` is your compatible endpoint (blank uses official OpenAI). No default or automatic alternate model is chosen.

In the backend PowerShell session, from the repository root:

```powershell
$env:DEMO_MODE='true'
$env:REPROBRIDGE_TEST_MODE='true' # Dedicated synthetic fixture session only
$env:CLINICAL_EVIDENCE_AGENT_ENABLED='true'
$env:LLM_MODE='replay'
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second shell, run `npm.cmd --prefix frontend run dev -- --host 127.0.0.1`; open the printed local URL and use the existing coordinator token. The feature branch is not merged automatically.

## Reset and smoke (under 60 seconds)

Run `.venv\Scripts\python.exe scripts/smoke_demo.py`. It confirms health/migrations, resets only the guarded synthetic fixtures, checks Amira **IN_WINDOW** and the uncertain patient **HOLD_DATING_UNCERTAIN**, checks configuration, makes a read-only live catalog request and exercises recorded replay. It prints PASS/FAIL without generation requests. Catalog reachability does not establish selected-model permission; the real recording reports establish that. Missing or rejected explanations cause FAIL.

Alternatively expand Admin, choose Reset TSP demo, then Confirm reset TSP demo. Wait for completion and **2026-11-22**. Amira-only reset is separately nested and requires Confirm reset; it restores preconception rather than the TSP scene. Reset demo date changes only the calendar. A fresh browser profile starts at the default demo date.

## Demo order

1. Dashboard: show Time-sensitive and Review first; open Amira.
2. Show the carried open obligation and server-computed W1. Contrast the uncertain-dating patient's hold; never infer a date for it.
3. Receive the clearly labelled simulated Hospital A records. Show the 2011 record (age 16), source/facility and pending policy link.
4. Explain the computed window / cited earlier finding. In replay, Admin has the small Replay mode label. Show any abstention honestly; recordings do not bypass guards.
5. Show evidence, clinician review and explicit verified closure as separate gates. Approval alone does not close work.

## Wi-Fi, model or replay failure

Choose modes explicitly by setting `LLM_MODE=live` or `replay` in the backend session and restarting that service. Never switch models silently. Rejected models require a permitted `OPENAI_MODEL`; do not weaken validation. Replay requires a matching real capture and exact source/policy/date context; reset and retry only the local replay if its context changed. Missing recordings, model errors or abstentions must be reported. The deterministic source/window views remain available; they are not a successful LLM explanation.

To record new real responses deliberately, use `scripts/record_demo_llm.py --output <new-local-directory>`; it uses isolated migrated synthetic databases, no retries, and refuses overwrite. It costs credits. Select cases explicitly; inspect result metrics and secret-stripped captures before use. Full settings and observed live limitations are in `docs/DEMO_HARDENING.md`. Never include keys, tokens or terminal environment dumps in recordings.
