# Ajyra AI — ReproBridge

A synthetic-data prototype for HealthX Ajyal on 22 November 2026. Follow a preconception obligation into pregnancy, route it for human review, and verify closure against the evidence and applicable illustrative rule.

## Run on Windows

Requires Python 3.12, Node.js with npm, and Docker Desktop for the default PostgreSQL database.

```powershell
Set-Location F:\ReproBridge
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
& .\scripts\Initialize-Demo.ps1
docker compose up -d --wait
```

Run the initializer once. It creates the ignored root `.env` with distinct random demo role tokens and a local PostgreSQL password. Use `& .\scripts\Initialize-Demo.ps1 -SQLite` on a fresh setup for the file-backed Windows option. With SQLite, skip the Compose command. For a native PostgreSQL instance, set `DATABASE_URL` in `.env` to the local database and run migrations.

In one PowerShell terminal:

```powershell
Set-Location F:\ReproBridge\backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
Set-Location F:\ReproBridge\frontend
npm.cmd run dev
```

Open [ReproBridge](http://127.0.0.1:5173), [API docs](http://127.0.0.1:8000/docs), or [health](http://127.0.0.1:8000/api/health). Sign in using the `COORDINATOR_TOKEN` from `.env`. Use the separate `REVIEWER_TOKEN` at the review step. Start with the [demo script](docs/DEMO_SCRIPT.md).

## Verify

Run the automated evaluation with `& .\scripts\Test-Demo.ps1 -PostgreSQL` from the repository root. It produces a summary, JUnit reports, and a Playwright JSON report in the ignored `test-reports` directory.

```powershell
Set-Location F:\ReproBridge\backend
$reprobridgeTemp = ".pytest_cache/run-$([guid]::NewGuid().ToString('N'))"
..\.venv\Scripts\python.exe -m pytest -q --basetemp=$reprobridgeTemp
# Optional: repeat on PostgreSQL using isolated per-test schemas.
$env:TEST_POSTGRES_URL = ((Get-Content -LiteralPath ../.env | Where-Object { $_.StartsWith('DATABASE_URL=') }) -replace '^DATABASE_URL=', '')
$reprobridgeTemp = ".pytest_cache/run-$([guid]::NewGuid().ToString('N'))"
..\.venv\Scripts\python.exe -m pytest -q --basetemp=$reprobridgeTemp

Set-Location F:\ReproBridge\frontend
npm.cmd run build
npm.cmd test
$env:E2E_BROWSER_CHANNEL = 'msedge'
npm.cmd run test:e2e
```

The browser test uses ports 8013 and 5183. In the default suite it uses an isolated SQLite file. With `-PostgreSQL`, the runner executes the journey twice in separate, freshly migrated PostgreSQL schemas and validates both downloaded bundles. With Edge unavailable, run `npx.cmd playwright install chromium` and unset `E2E_BROWSER_CHANNEL` in that terminal.

For the database and API restart check on the local Compose service, run `.\.venv\Scripts\python.exe scripts\verify_postgres.py restart test-reports\restart.json` from the repository root.

## v0.4 judge demo

Open the [v0.4 judge walkthrough](docs/V04_JUDGE_WALKTHROUGH.md) for Amira’s metabolic-assessment story, review flow, and reset procedure. See the [clinical scenario](docs/V04_CLINICAL_SCENARIO.md) and [verification](docs/V04_TEST_REPORT.md).

## v0.3 judge demo

Start with the [judge walkthrough](docs/V03_JUDGE_WALKTHROUGH.md). The coordinator can expand **Reset Amira demo** on Population Intelligence to archive the fixture run and restore preconception. Its scope guards preserve unrelated patient records and refuse nonfixture data attached to Amira.

The [release assessment](docs/V03_DEMO_READINESS.md) links the test report and screenshot set.

## Documentation

- [Product scope](docs/PRODUCT_SCOPE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [FHIR contracts](docs/FHIR_CONTRACTS.md)
- [Clinical rules](docs/CLINICAL_RULES.md)
- [Security and governance](docs/SECURITY_AND_GOVERNANCE.md)
- [Implementation backlog](docs/IMPLEMENTATION_BACKLOG.md)
- [v0.2 test report](docs/V02_TEST_REPORT.md)
- [v0.1 test report](docs/TEST_REPORT.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
- [v0.2 release assessment](docs/V02_DEMO_READINESS.md)
