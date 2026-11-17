import pytest

from app.agent import reconcile
from app.rules import matches, observation

CODE = "follow-up-reconciled"


@pytest.mark.parametrize("status, accepted", [("final", True), ("preliminary", False), ("entered-in-error", False)])
def test_completion_requires_final_status(status, accepted):
    record = observation("demo-unit", "demo-unit-evidence", CODE, "verified")
    assert matches({**record, "status": status}, CODE, "verified") is accepted


def test_matching_rejects_foreign_code_system_and_arbitrary_text():
    record = observation("demo-unit", "demo-unit-evidence", CODE, "appointment booked")
    assert not matches(record, CODE, "verified")
    record["valueString"] = "verified"
    record["code"]["coding"][0]["system"] = "https://different.example"
    assert not matches(record, CODE, "verified")


@pytest.mark.parametrize("source_qualified, completion, finding", [
    (True, [], "missing_closure_evidence"),
    (True, ["verified"], "evidence_available"),
    (True, ["verified", "revoked"], "conflicting_or_unqualified_evidence"),
    (False, ["verified"], "conflicting_or_unqualified_evidence"),
])
def test_reconcile_depends_on_scoped_evidence(source_qualified, completion, finding):
    records = [observation("demo-unit", f"demo-unit-{index}", CODE, value)
               for index, value in enumerate(completion)]
    assert reconcile({"authorized_records": records, "closure_code": CODE,
                      "source_qualified": source_qualified})["finding"] == finding
