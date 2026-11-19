import re
from datetime import date
from uuid import uuid4
from fastapi import APIRouter, Request, Response
from app.clinical.contracts import Contract
from app.prevention import tsp


class ClockDate(Contract):
    as_of: date


def router(Reader, Coordinator, write):
    api = APIRouter(prefix="/api/v1/tsp", tags=["Synthetic prevention windows"])

    def session(request, response):
        identifier = request.cookies.get("reprobridge-demo-session", "")
        if not re.fullmatch(r"[a-f0-9]{32}", identifier):
            identifier = uuid4().hex
            if tsp.demo_enabled():
                response.set_cookie("reprobridge-demo-session", identifier, httponly=True, samesite="strict", path="/api")
        return identifier

    @api.get("/clock")
    def clock(request: Request, response: Response, actor: Reader):
        return write(tsp.clock, session(request, response))

    @api.post("/clock")
    def advance(body: ClockDate, request: Request, response: Response, actor: Coordinator):
        return write(tsp.clock, session(request, response), body.as_of)

    @api.post("/clock/reset")
    def reset_clock(request: Request, response: Response, actor: Coordinator):
        return write(tsp.clock, session(request, response), None, True)

    @api.get("/patients/{patient_id}/window")
    def window(patient_id: str, request: Request, response: Response, actor: Reader):
        return write(tsp.patient_window, actor, patient_id, session(request, response))

    @api.get("/queue")
    def queue(request: Request, response: Response, actor: Reader):
        return write(tsp.queue, actor, session(request, response))

    return api
