from fastapi import APIRouter,Request
from app import history


def router(Reader,Coordinator,write):
    api=APIRouter(prefix="/api/v1/history-handoff",tags=["Simulated provider exchange"])
    @api.post("/seed")
    def seed(actor:Coordinator):return write(history.seed,actor)
    @api.post("/patients/{patient_id}/receive")
    def receive(patient_id:str,actor:Coordinator):return write(history.receive,actor,patient_id)
    @api.get("/patients/{patient_id}")
    def view(patient_id:str,request:Request,actor:Reader):
        return write(history.view,actor,patient_id,request.cookies.get("reprobridge-demo-session"))
    return api
