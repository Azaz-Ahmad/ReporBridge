from fastapi import APIRouter, HTTPException
from app.investigation import service as investigation
from app.investigation.contracts import RunRequest
from app.prevention import service
from app.prevention.contracts import (
    AssignPolicy, CreateDecision, InvestigationRequest, PolicyState, RecordDecision, TimingPolicy, Transition,
)


def router(Reader, Coordinator, Reviewer, write):
    api = APIRouter(prefix="/api/v1/prevention", tags=["Prevention decisions"])

    @api.get("/snapshot")
    def snapshot(actor: Reader, patient_id: str | None = None):
        return write(service.snapshot, actor, patient_id)

    @api.post("/decisions")
    def create(request: CreateDecision, actor: Coordinator):
        return write(service.create, actor, request)

    @api.get("/decisions/{identifier}")
    def get(identifier: str, actor: Reader):
        def read(connection):
            decision = service.evaluate(connection, service.get(connection, actor, identifier, active=False))
            return service.view(connection, decision)
        return write(read)

    @api.post("/decisions/{identifier}/transition")
    def transition(identifier: str, request: Transition, actor: Reader):
        if actor not in {"coordinator", "reviewer"}:
            raise HTTPException(403, "A coordinator or reviewer role is required.")
        return write(service.transition, actor, identifier, request)

    @api.post("/decisions/{identifier}/record")
    def record(identifier: str, request: RecordDecision, actor: Reviewer):
        return write(service.record, actor, identifier, request)

    @api.post("/decisions/{identifier}/follow-up/{index}")
    def follow_up(identifier: str, index: int, actor: Coordinator):
        return write(service.start_follow_up, actor, identifier, index)

    @api.post("/policies")
    def create_policy(request: TimingPolicy, actor: Coordinator):
        return write(service.create_policy, actor, request)

    @api.post("/policies/{identifier}/state")
    def policy_state(identifier: str, request: PolicyState, actor: Coordinator):
        return write(service.policy_state, actor, identifier, request)

    @api.post("/decisions/{identifier}/policy")
    def assign_policy(identifier: str, request: AssignPolicy, actor: Coordinator):
        return write(service.assign_policy, actor, identifier, request)

    @api.get("/decisions/{identifier}/investigations")
    def runs(identifier: str, actor: Reader):
        return write(service.investigation_runs, actor, identifier)

    @api.post("/decisions/{identifier}/investigations")
    def investigate(identifier: str, request: InvestigationRequest, actor: Coordinator):
        prepared = write(service.prepare_investigation, actor, identifier, request)
        binding = prepared["binding"]
        run = investigation.run_investigation(actor, RunRequest(
            patient_id=binding["patient_id"], question=prepared["question"],
            request_id=identifier + "-" + request.request_id, synthetic_only=True), write,
            trusted_decision=binding)
        return write(service.finish_investigation, actor, identifier, run)

    @api.post("/demo/timing")
    def timing_demo(actor: Coordinator):
        from app.prevention.fixtures import timing_demo
        return write(timing_demo, actor)

    return api
