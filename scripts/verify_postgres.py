"""Run the v0.2 browser and restart checks against newly migrated PostgreSQL schemas."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
from secrets import token_urlsafe
import statistics
import subprocess
import sys
import time
from uuid import uuid4

from dotenv import dotenv_values
import httpx
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
ORIGIN = "http://127.0.0.1:8023/api"


@contextmanager
def scratch_schema():
    database = make_url(dotenv_values(ROOT / ".env")["DATABASE_URL"])
    if database.get_backend_name() != "postgresql":
        raise ValueError("The v0.2 verification requires a PostgreSQL DATABASE_URL.")
    schema = "v02_" + uuid4().hex
    engine = create_engine(database, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {schema}")
    try:
        yield database.update_query_dict({"options": f"-csearch_path={schema}"})
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA {schema} CASCADE")
        engine.dispose()


def browser(report_path):
    with scratch_schema() as database:
        env = {
            **os.environ, "REPROBRIDGE_E2E_DATABASE_URL": database.render_as_string(hide_password=False),
            "PLAYWRIGHT_JSON_OUTPUT_FILE": str(report_path),
            **{f"E2E_{role}_TOKEN": token_urlsafe() for role in ("COORDINATOR", "REVIEWER", "VIEWER")},
        }
        subprocess.run(["cmd.exe", "/d", "/c", "npm.cmd", "run", "test:e2e", "--", "--reporter=line,json"],
                       cwd=ROOT / "frontend", env=env, check=True)
        result = json.loads(report_path.read_text(encoding="utf-8"))
        if result["stats"]["expected"] != 1 or result["stats"]["unexpected"] != 0:
            raise RuntimeError("Expected exactly one successful, fresh browser journey.")
        suite, = result["suites"]
        spec, = suite["specs"]
        test, = spec["tests"]
        attempt, = test["results"]
        exported = next(item["path"] for item in attempt["attachments"] if item["name"] == "FHIR R4 export")
        bundle_path = report_path.with_name(report_path.stem + "-amira-r4.json")
        bundle_path.write_bytes(Path(exported).read_bytes())
        subprocess.run([sys.executable, "-c", """
import json
from pathlib import Path
import sys
from app.fhir import check_references, structure_errors
bundle = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert not structure_errors(bundle)
check_references([entry['resource'] for entry in bundle['entry']])
print('Downloaded Amira bundle passed FHIR R4 structure and patient-local reference checks.')
""", str(bundle_path)], cwd=BACKEND, check=True)


@contextmanager
def api_process(env):
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8023"],
        cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_api(process)
        yield process
    finally:
        if process.poll() is None:
            subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, check=True)
            process.wait(timeout=10)


def wait_for_api(process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Verification API exited before readiness.")
        try:
            response = httpx.get(ORIGIN + "/health", timeout=2)
            if response.is_success and response.json()["database"] == "postgresql":
                return
        except httpx.TransportError:
            pass
        time.sleep(.3)
    raise RuntimeError("Verification API did not report PostgreSQL readiness.")


def restart(report_path):
    with scratch_schema() as database:
        env = {
            **os.environ, "DATABASE_URL": database.render_as_string(hide_password=False),
            **{f"{role}_TOKEN": token_urlsafe() for role in ("COORDINATOR", "REVIEWER", "VIEWER")},
        }
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)
        timings = {}

        def request(client, method, path, metric=None):
            started = time.perf_counter()
            response = client.request(method, path).raise_for_status()
            if metric:
                timings.setdefault(metric, []).append(round((time.perf_counter() - started) * 1000, 2))
            return response.json()

        headers = {"Authorization": "Bearer " + env["COORDINATOR_TOKEN"]}
        with api_process(env) as first, httpx.Client(base_url=ORIGIN, headers=headers, timeout=10) as client:
            request(client, "POST", "/demo/seed")
            for _ in range(8):
                request(client, "POST", "/patients/demo-amira/evaluate", "rule_evaluation")
                request(client, "GET", "/snapshot", "snapshot")
            request(client, "POST", "/patients/demo-amira/pregnancy", "register_pregnancy")
            current = request(client, "GET", "/snapshot")
            for obligation in current["clinical_obligations"]:
                request(client, "POST", f"/obligations/{obligation['id']}/agent", "fresh_agent_execution")
            before = request(client, "GET", "/snapshot")
            postgres_restart_started = time.perf_counter()
            subprocess.run(["docker", "compose", "restart", "postgres"], cwd=ROOT, check=True)
            wait_for_api(first)
            db_restart_ms = round((time.perf_counter() - postgres_restart_started) * 1000)
            assert request(client, "GET", "/snapshot") == before
        api_restart_started = time.perf_counter()
        with api_process(env), httpx.Client(base_url=ORIGIN, headers=headers, timeout=10) as client:
            api_restart_ms = round((time.perf_counter() - api_restart_started) * 1000)
            assert request(client, "GET", "/snapshot") == before
            request(client, "POST", "/patients/demo-amira/pregnancy")
            assert request(client, "GET", "/snapshot") == before

        engine = create_engine(database)
        with engine.connect() as connection:
            evidence_plan = connection.exec_driver_sql(
                "EXPLAIN (ANALYZE, FORMAT JSON) SELECT resource FROM clinical_evidence WHERE patient_id = %s",
                ("demo-amira",),
            ).scalar_one()[0]
        engine.dispose()
        result = {
            "databaseRestartPersisted": True, "apiRestartPersisted": True, "transitionReplayUnchanged": True,
            "postgresRecoveryMs": db_restart_ms, "apiRecoveryMs": api_restart_ms,
            "observedMs": {name: {"samples": len(samples), "median": statistics.median(samples),
                                  "max": max(samples)} for name, samples in timings.items()},
            "patientEvidenceQuery": {"plan": evidence_plan["Plan"]["Node Type"],
                                     "rows": evidence_plan["Plan"]["Actual Rows"],
                                     "executionMs": evidence_plan["Execution Time"]},
        }
        report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("browser", "restart"))
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    path = args.report.resolve()
    path.relative_to(ROOT / "test-reports")
    path.parent.mkdir(parents=True, exist_ok=True)
    {"browser": browser, "restart": restart}[args.check](path)


if __name__ == "__main__":
    main()
