from datetime import date, timedelta
import pytest
from app.prevention.window import calculate, default_policy

ORIGIN = date(2026, 6, 1)
REGISTERED = ORIGIN + timedelta(days=50)


def run(day, **kwargs):
    return calculate(default_policy(), due_date=ORIGIN + timedelta(days=280), registered_on=REGISTERED,
                     as_of=ORIGIN + timedelta(days=day), carried_obligation=True, **kwargs)


@pytest.mark.parametrize("window,day,status", [
    ("W1",49,"DUE_SOON"),("W1",50,"IN_WINDOW"),("W1",104,"IN_WINDOW"),("W1",105,"WINDOW_PASSED"),
    ("W2",167,"DUE_SOON"),("W2",168,"IN_WINDOW"),("W2",202,"IN_WINDOW"),("W2",203,"WINDOW_PASSED"),
    ("W2",160,"NOT_YET_DUE"),("W2",161,"DUE_SOON")])
def test_boundaries(window, day, status):
    assert next(w for w in run(day)["windows"] if w["id"] == window)["status"] == status


def test_completion_and_policy():
    assert run(210, completion_dates=[ORIGIN+timedelta(days=203)])["status"] == "COMPLETED_LATE"
    assert run(202, completion_dates=[ORIGIN+timedelta(days=202)])["status"] == "COMPLETED_IN_WINDOW"
    assert calculate(None, due_date=None, registered_on=None, as_of=ORIGIN)["status"] == "NO_POLICY"
    assert run(100)["citation"] == "CITATION_PENDING_CLINICAL_CONFIRMATION"


from app.prevention.window import resolve_dating


def dating(kind, day, version="1"):
    return {"id": kind, "version": version, "digest": "synthetic", "quality": {"state": "valid"},
        "resource": {"resourceType": "Observation", "status": "final", "code": {"coding": [{"code": kind}]},
                     "valueDateTime": day.isoformat()}}


@pytest.mark.parametrize("difference,held", [(0,False),(7,False),(8,True)])
def test_dating_agreement_and_conflict(difference, held):
    policy=default_policy()
    sources=[dating("tsp-lmp",ORIGIN),dating("tsp-ultrasound-edd",ORIGIN+timedelta(days=280+difference),"2")]
    resolved=resolve_dating(policy,sources)
    result=calculate(policy,due_date=resolved["due_date"],registered_on=REGISTERED,as_of=REGISTERED,
                     inputs=resolved["inputs"],missing_evidence=resolved["missing_evidence"])
    assert (result["status"]=="HOLD_DATING_UNCERTAIN") is held
    assert result["inputs_used"][1]["version"]=="2"
    if held:
        assert result["windows"]==[] and result["window_start"] is None and result["reviewer_questions"]


def test_missing_and_invalid_dating():
    assert resolve_dating(default_policy(),[])["due_date"] is None
    item=dating("tsp-lmp",ORIGIN); item["quality"]["state"]="superseded"
    assert resolve_dating(default_policy(),[item])["due_date"] is None


from test_workflow import client, seed  # noqa: F401


def test_api_authorization_clock_and_hold(client, monkeypatch):
    seed(client)
    base="/v1/tsp"
    assert client(base+"/patients/demo-amira/window",role=None,method="GET").status_code==401
    assert client(base+"/patients/demo-missing/window",method="GET").status_code==404
    monkeypatch.delenv("DEMO_MODE",raising=False)
    assert client(base+"/clock",body={"as_of":"2026-11-23"}).status_code==403
    monkeypatch.setenv("DEMO_MODE","true")
    assert client(base+"/clock",method="GET").json()["as_of"]=="2026-11-22"
    assert client(base+"/clock",role="viewer",body={"as_of":"2026-11-23"}).status_code==403
    assert client(base+"/clock",body={"as_of":"2026-11-23"}).json()["as_of"]=="2026-11-23"
    result=client(base+"/patients/demo-amira/window",method="GET").json()
    assert result["status"]=="HOLD_DATING_UNCERTAIN" and result["clock"]["demo_mode"]
    assert result["as_of"]=="2026-11-23" and result["window_start"] is None
    assert client(base+"/clock/reset").json()["as_of"]=="2026-11-22"
    assert client(base+"/clock",body={"as_of":"not-a-date"}).status_code==422
