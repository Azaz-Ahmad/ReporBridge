"""Read-only SIMULATED facility labels over unchanged FHIR/receipt fields."""
from sqlalchemy import select
from app.clinical.schema_v1 import receipts, registry

ORGANIZATION_SYSTEM = "https://reprobridge.example/simulated-organizations"
NAMES = {"hospital-a": "Hospital A", "hospital-b": "Hospital B"}


def origin(resource):
    references = [resource.get("serviceProvider", {}), *resource.get("performer", []), *resource.get("author", [])]
    for reference in references:
        if reference.get("type") == "Organization" and reference.get("display") in NAMES.values():
            return reference["display"]
    return None


def facility(connection, row):
    if row["patient_id"] != "demo-handoff":
        return {}
    name = origin(row["resource"])
    if not name:
        return {}
    received = connection.execute(select(receipts.c.received).join(registry,
        registry.c.id == receipts.c.evidence_id).where(registry.c.patient_id == row["patient_id"],
        registry.c.resource_id == row["resource_id"], registry.c.kind == row["kind"],
        registry.c.source == row["source"], registry.c.scope == row["scope"],
        receipts.c.event_id.startswith("simulated-handoff-")).order_by(receipts.c.received).limit(1)).scalar_one_or_none()
    return {"facility": {"simulation": True, "origin": name,
        "received_at": received, "receiving": "Hospital B" if received else None,
        "transport": "received via simulated exchange" if received else "SIMULATED origin record"}}


def export_agents(action):
    detail = action["detail"]
    if not detail.get("simulation"):
        return []
    return [{"who": detail[key]} for key in ("origin_facility", "receiving_facility") if detail.get(key)]
