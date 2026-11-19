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
