from fastapi import APIRouter,Request
from app import history
from app.prevention.contracts import InvestigationRequest


def router(Reader,Coordinator,write):
    api=APIRouter(prefix="/api/v1/history-handoff",tags=["Simulated provider exchange"])
    @api.post("/seed")
    def seed(actor:Coordinator):return write(history.seed,actor)
    @api.post("/patients/{patient_id}/receive")
    def receive(patient_id:str,request:Request,actor:Coordinator):return write(history.receive,actor,patient_id,request.cookies.get("reprobridge-demo-session"))
    @api.get("/patients/{patient_id}")
    def view(patient_id:str,request:Request,actor:Reader):
        return write(history.view,actor,patient_id,request.cookies.get("reprobridge-demo-session"))
    @api.post("/patients/{patient_id}/investigations")
    def investigate(patient_id:str,request:Request,body:InvestigationRequest,actor:Coordinator):
        from app import history_guard
        from app.investigation import service
        from app.investigation.contracts import RunRequest
        binding=write(history_guard.bind,actor,patient_id,request.cookies.get("reprobridge-demo-session"))
        return service.run_investigation(actor,RunRequest(patient_id=patient_id,request_id="history-"+body.request_id,
            question="Explain the exact cited earlier source facts for clinician review; use only the server-rendered pending rule and existing window.",synthetic_only=True),write,trusted_window=binding)
    @api.post("/patients/{patient_id}/explanations")
    def explain(patient_id:str,request:Request,body:InvestigationRequest,actor:Coordinator):
        from app import explanations,history_guard
        from app.investigation.contracts import RunRequest
        binding=write(history_guard.bind,actor,patient_id,request.cookies.get("reprobridge-demo-session"))
        return explanations.run(actor,RunRequest(patient_id=patient_id,question="Validate exact server-prepared historical source and prevention explanation fields.",request_id="fields-history-"+body.request_id,synthetic_only=True),write,binding)
    return api
