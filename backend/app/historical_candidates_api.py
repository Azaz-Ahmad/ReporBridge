from typing import Literal
from fastapi import APIRouter,Request
from pydantic import Field
from app.clinical.contracts import Contract
from app import historical_candidates as service
class CandidateReview(Contract):
    decision:Literal["confirm","dismiss"]
    rationale:str=Field(min_length=3,max_length=1000)
def router(Reader,Reviewer,write):
    api=APIRouter(prefix="/api/v1/historical-candidates",tags=["Historical candidates — clinician confirmation required"])
    @api.get("")
    def queue(actor:Reader):return write(service.queue,actor)
    @api.get("/patients/{patient_id}")
    def patient(patient_id:str,request:Request,actor:Reader):return write(service.list_patient,actor,patient_id,request.cookies.get("reprobridge-demo-session"))
    @api.post("/{identifier}/review")
    def review(identifier:str,body:CandidateReview,request:Request,actor:Reviewer):
        return write(service.review,actor,identifier,body.decision,body.rationale,request.cookies.get("reprobridge-demo-session"))
    return api
