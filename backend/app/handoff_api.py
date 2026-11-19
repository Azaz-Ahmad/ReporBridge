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

    return api
