"""Pure deterministic timing. All configured policies in this increment are illustrative."""
from datetime import UTC, datetime


def evaluate(policy, as_of=None):
    if not policy or policy["status"] != "active":
        return {"state": "not_established", "label": "Timing not established.", "due_at": None,
                "policy_id": policy["id"] if policy else None,
                "reason": "policy_" + policy["status"] if policy else "no_policy"}
    moment = as_of or datetime.now(UTC)
    due = datetime.fromisoformat(policy["definition"]["due_at"])
    remaining = (due - moment).total_seconds()
    state = "overdue" if remaining < 0 else "due_soon" if remaining <= policy["definition"]["due_soon_seconds"] else "scheduled"
    return {"state": state, "label": state.replace("_", " ").capitalize(),
            "due_at": due.isoformat(), "policy_id": policy["id"], "reason": "illustrative_policy"}
