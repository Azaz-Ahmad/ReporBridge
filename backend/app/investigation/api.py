"""Role- and patient-scoped HTTP entry points for evidence investigations."""
from fastapi import APIRouter
from app import db
from app.investigation import service
from app.investigation.contracts import Review, RunRequest
from app.multi.contracts import MultiRequest


def router(Reader, Coordinator, Reviewer, write):
    api = APIRouter(prefix="/api/v1/agents/clinical-evidence", tags=["Clinical Evidence Agent"])

    @api.get("/status")
    def status(actor: Reader):
        return service.status()

    @api.post("/runs")
    def create(request: RunRequest, actor: Coordinator):
        return service.run_investigation(actor, request, write)

    @api.post("/runs/multi-agent")
    def create_multi(request: MultiRequest, actor: Coordinator):
        from app.multi.engine import run_investigation
        return run_investigation(actor, request, write)

    @api.get("/runs")
    def list_runs(patient_id: str, actor: Reader):
        with db.engine.begin() as connection:
            return service.list_runs(connection, actor, patient_id)

    @api.get("/runs/{run_id}")
    def get(run_id: str, actor: Reader):
        return write(service.fetch, actor, run_id)

    @api.get("/runs/{run_id}/trace")
    def trace(run_id: str, actor: Reader):
        run = write(service.fetch, actor, run_id)
        return {key: run["detail"].get(key) for key in
                ("trace", "tool_history", "model_history", "evidence_references", "usage", "duration_ms", "error", "validation", "multi_agent", "denied_tool_requests")}

    @api.get("/runs/{run_id}/review-packet")
    def packet(run_id: str, actor: Reader):
        return write(service.fetch, actor, run_id)["detail"]["packet"]

    @api.post("/runs/{run_id}/submit")
    def submit(run_id: str, actor: Coordinator):
        return write(service.submit, actor, run_id)

    @api.post("/runs/{run_id}/review")
    def review(run_id: str, request: Review, actor: Reviewer):
        return write(service.review, actor, run_id, request)

    return api
