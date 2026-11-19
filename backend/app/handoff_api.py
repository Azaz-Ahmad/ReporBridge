from fastapi import APIRouter
from app import handoff


def router(Reader, Coordinator, write):
    api = APIRouter(prefix="/api/v1/simulated-handoff", tags=["SIMULATED facility exchange"])

    @api.post("/demo/seed")
    def seed(actor: Coordinator):
        return write(handoff.seed, actor)

    @api.get("/patients/{patient_id}")
    def view(patient_id: str, actor: Reader):
        return write(handoff.view, actor, patient_id)

    @api.post("/patients/{patient_id}/receive")
    def receive(patient_id: str, actor: Coordinator):
        return write(handoff.receive, actor, patient_id)

    @api.post("/patients/{patient_id}/origin/invalidate")
    def invalidate(patient_id: str, actor: Coordinator):
        return write(handoff.invalidate_origin, actor, patient_id)

    return api
