"""Read-only coordination projection. Never part of clinical calculation or model context."""
import json
from pathlib import Path
from app.clinical.access import permitted
from app.prevention import tsp

POLICY_FILE = Path(__file__).with_name("coordination_policy_v1.json")


def policy():
    return json.loads(POLICY_FILE.read_text(encoding="utf-8"))


def next_action(status, definition=None):
    definition = definition if definition is not None else policy()
    # Unknown states fail closed: no invented action or automatic routing.
    return dict(definition["actions"].get(status, {"action": None, "owner_role": None}))


def project(result):
    definition = policy()
    matching = (result["status"] == "NO_POLICY" or
                (result["policy_id"], result["policy_version"]) ==
                (definition["window_policy_id"], definition["window_policy_version"]))
    action = next_action(result["status"], definition) if matching else {"action": None, "owner_role": None}
    return {**result, "coordination": {**action, "policy_id": definition["id"],
            "policy_version": definition["version"], "scope": definition["scope"], "policy_matched": matching}}


def patient(connection, actor, patient_id, session_id=None):
    return project(tsp.patient_window(connection, actor, patient_id, session_id))


def queue(connection, actor, session_id=None):
    return [patient(connection, actor, identifier, session_id) for identifier in sorted(permitted(connection, actor))]
