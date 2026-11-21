"""Explicit DEMO_MODE wrapper; all correction/reopening logic stays in existing M08."""
from app import db, service
from app.clinical.access import authorize, fail, now
from app.clinical.contracts import Event
from app.clinical.events import process
from app.clinical.gateway import LocalFHIRProvider
from app.prevention.tsp_demo import enabled
from app.rules import DEMO_TAG


def correct_closing_evidence(connection, actor, obligation_id, evidence_id):
    enabled()
    obligation = service.find(connection, db.obligations, obligation_id, required=True)
    context = authorize(connection, actor, obligation["patient_id"])
    if obligation["status"] != "closed":
        fail(409, "closed_obligation_required", "Select a verified closed obligation before simulating a correction.")
    closures = service.rows(connection, db.closures, db.closures.c.obligation_id == obligation_id,
                            db.closures.c.evidence_id == evidence_id)
    candidates = [record for record in service.closure_candidates(connection, obligation) if record["id"] == evidence_id]
    if not closures or len(candidates) != 1 or DEMO_TAG not in candidates[0].get("meta", {}).get("tag", []):
        fail(409, "synthetic_closing_evidence_required", "Only recorded synthetic closing evidence may be corrected by this demo control.")
    resource = candidates[0]
    chain = [row for row in LocalFHIRProvider(connection).catalog(context)
             if row["resource_id"] == evidence_id and row["kind"] == "Observation"]
    if not chain or any(row["source"] != "workflow" for row in chain):
        fail(409, "workflow_closing_evidence_required", "The demo control is limited to existing workflow closing observations.")
    prior = max(chain, key=lambda row: row["version"])
    if prior["resource"] != resource or prior["status"] != "final":
        fail(409, "closing_evidence_changed", "Closing evidence changed; refresh and review before simulating a correction.")
    result = process(connection, context, Event(source="workflow",
        event_id="demo-closing-correction-" + obligation_id + "-v" + str(prior["version"] + 1),
        event_time=now(), resource=resource, version=prior["version"] + 1, action="invalidate"))
    current = service.find(connection, db.obligations, obligation_id, required=True)
    return {**result, "simulation": True, "obligation_status": current["status"], "owner": current["owner"]}
