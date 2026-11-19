"""Date-only policy evaluator. No model, system clock, database or glucose interpretation."""
from datetime import date, timedelta
import json
from pathlib import Path

CITATION_PENDING_CLINICAL_CONFIRMATION = "CITATION_PENDING_CLINICAL_CONFIRMATION"


def default_policy():
    return json.loads(Path(__file__).with_name("tsp_policy_v1.json").read_text(encoding="utf-8"))


def calculate(policy, *, due_date, registered_on, as_of, carried_obligation=False,
              completion_dates=(), inputs=(), missing_evidence=()):
    result = {"status": "NO_POLICY", "as_of": as_of.isoformat(), "timezone": "Asia/Dubai",
              "policy_id": policy.get("id") if policy else None,
              "policy_version": policy.get("version") if policy else None,
              "citation": CITATION_PENDING_CLINICAL_CONFIRMATION,
              "clinical_confirmation": "pending clinical confirmation", "window_start": None,
              "window_end": None, "windows": [], "inputs_used": list(inputs),
              "missing_evidence": list(missing_evidence), "reviewer_questions": []}
    if not policy or policy.get("kind") != "gestational_window":
        return result
    if due_date is None or registered_on is None or missing_evidence:
        result.update(status="HOLD_DATING_UNCERTAIN", reviewer_questions=[
            "Review missing or conflicting pregnancy dating evidence before establishing a window."])
        return result
    origin = due_date - timedelta(days=policy["gestation_days"])
    for definition in policy["windows"]:
        if definition.get("requires_carried_obligation") and not carried_obligation:
            continue
        start = registered_on if definition.get("start") == "pregnancy_registration" else origin + timedelta(days=definition["start_ga_day"])
        end = origin + timedelta(days=definition["end_ga_day"])
        completed = sorted(day for day in completion_dates if day >= start and day <= as_of)
        # A result prior to the window does not satisfy it. Only evidence dates are used.
        if completed:
            state = "COMPLETED_IN_WINDOW" if completed[0] <= end else "COMPLETED_LATE"
        elif as_of > end:
            state = "WINDOW_PASSED"
        elif as_of >= start:
            state = "IN_WINDOW"
        elif (start - as_of).days <= policy["due_soon_days"]:
            state = "DUE_SOON"
        else:
            state = "NOT_YET_DUE"
        result["windows"].append({"id": definition["id"], "label": definition["label"],
            "status": state, "window_start": start.isoformat(), "window_end": end.isoformat(),
            "completion_date": completed[0].isoformat() if completed else None})
    windows = result["windows"]
    # Preserve W1 history while moving the active display to W2 after W1 ends.
    active = next((w for w in windows if as_of <= date.fromisoformat(w["window_end"])), windows[-1] if windows else None)
    if active:
        result.update({key: active[key] for key in ("status", "window_start", "window_end")}, active_window=active["id"])
    return result
