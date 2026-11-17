"""Append versioned evidence and durable notifications in the caller's write transaction."""
import re
from typing import get_args
from uuid import uuid4

from sqlalchemy import select

from app import db
from app.clinical.access import authorize, fail, now, resolve
from app.clinical.contracts import ResourceType
from app.clinical.gateway import LocalFHIRProvider, reference_key, workflow_scope
from app.clinical.normalize import digest, extract_document, normalize, source_status, stamp, validate
from app.clinical.schema_v1 import changes, chunks, receipts, registry
from app.fhir import references, TARGET_TYPES
from app.rules import code_matches


def process(connection, context, event):
    from app import service

    context = authorize(connection, context.role, context.patient_id)
    if context.role != "coordinator":
        fail(403, "ingestion_forbidden", "Clinical ingestion requires coordinator authorization.")
    patient_id = context.patient_id
    if event.external_id:
        resolve(connection, context, event.source, event.external_id)
    resource = event.resource
    kind, identifier = resource.get("resourceType"), resource.get("id")
    if kind not in get_args(ResourceType) or not isinstance(identifier, str) or not re.fullmatch(
            r"demo-[A-Za-z0-9.-]{1,59}", identifier):
        fail(422, "invalid_resource", "Use a supported FHIR resource with a synthetic identifier.")
    if kind == "Patient":
        fail(422, "immutable_identity", "Provision canonical patients through the existing synthetic workflow.")
    validate(resource, patient_id, event.version, kind)
    event_time = stamp(event.event_time)
    received = now()
    event_hash = digest({**event.model_dump(mode="json", exclude={"event_id", "event_time"}), "event_time": event_time})
    receipt = connection.execute(select(receipts).where(
        receipts.c.source == event.source, receipts.c.event_id == event.event_id,
        receipts.c.patient_id == patient_id)).mappings().first()
    if receipt:
        if receipt["digest"] != event_hash or receipt["patient_id"] != patient_id:
            fail(409, "replay_conflict", "Event identifier conflicts with a previous event.")
        return {"status": "duplicate", "evidence_id": receipt["evidence_id"]}

    rows = LocalFHIRProvider(connection).catalog(context)
    key = f"{kind}/{identifier}"
    chain = [row for row in rows if reference_key(row) == key]
    if any(row["source"] != event.source for row in chain):
        fail(409, "source_conflict", "This logical resource is already owned by another source.")
    prior = max(chain, key=lambda row: row["version"], default=None)
    if event.source == "workflow" and (not prior or kind != "Observation"):
        fail(422, "workflow_correction_only", "This source supports corrections to existing workflow observations.")
    available = {reference_key(row) for row in rows}
    refs = set(references(resource))
    if resource.get("contained") or not refs <= available or key in refs:
        fail(422, "invalid_reference", "References must resolve to other records in the same patient scope.")
    for (resource_type, field), types in TARGET_TYPES.items():
        if kind == resource_type and field in resource and any(
                ref.split("/", 1)[0] not in types for ref in references(resource[field])):
            fail(422, "invalid_reference_type", "Reference targets an incompatible resource type.")
    if kind == "DocumentReference":
        if any(not target.startswith("Encounter/") for target in
               references((resource.get("context") or {}).get("encounter", []))):
            fail(422, "invalid_reference_type", "Document encounter references must target local encounters.")
        for target in references(resource.get("relatesTo", [])):
            if not target.startswith("DocumentReference/"):
                fail(422, "invalid_document_link", "Document relationships must refer to a local DocumentReference.")

    content_hash = digest(resource)
    status = "invalidated" if event.action == "invalidate" else source_status(resource)
    log_values = dict(source=event.source, event_id=event.event_id, patient_id=patient_id,
                      digest=event_hash, event_time=event_time, received=received, actor=context.role)
    same = next((row for row in chain if row["version"] == event.version), None)
    if same:
        if same["digest"] != content_hash or same["status"] != status:
            fail(409, "version_conflict", "This source version already has different content or state.")
        materialize(connection, same)
        connection.execute(receipts.insert().values(**log_values, evidence_id=same["id"]))
        return {"status": "duplicate", "evidence_id": same["id"]}
    if event.version != (prior["version"] + 1 if prior else 1) or (prior and prior["event_time"] and event_time < prior["event_time"]):
        fail(409, "out_of_order", "A missing or later version must be reconciled before this event can apply.")
    if event.action == "invalidate" and not prior:
        fail(409, "missing_predecessor", "Invalidation requires an existing source version.")

    clinical_time, normalized = normalize(resource, received, event_time)
    normalized["source_event_time"] = event.event_time.isoformat()
    parts = []
    if kind == "DocumentReference":
        normalized["document"], parts = extract_document(resource)
        if ((status == "current" and resource.get("docStatus") == "entered-in-error") or
                (status == "entered-in-error" and resource.get("docStatus") == "final")):
            normalized["warnings"].append("conflicting_document_status")
    if prior:
        materialize(connection, prior)
    evidence_id = uuid4().hex
    connection.execute(registry.insert().values(id=evidence_id, patient_id=patient_id, source=event.source,
        scope=workflow_scope(connection, patient_id) if event.source == "workflow" else "clinical",
        kind=kind, resource_id=identifier, version=event.version, event_time=event_time, clinical_time=clinical_time,
        received=received, status=status, digest=content_hash, actor=context.role,
        supersedes=prior["id"] if prior else None, resource=resource, normalized=normalized))
    if parts:
        connection.execute(chunks.insert(), [dict(evidence_id=evidence_id, position=position, section=section, body=body)
            for position, (section, body) in enumerate(parts)])
    connection.execute(receipts.insert().values(**log_values, evidence_id=evidence_id))
    affected = []
    if event.source == "workflow":
        original = chain[0]["resource"] if len(chain) == 1 else min(chain, key=lambda row: row["version"])["resource"]
        affected = reconsider_workflow(connection, service, context, original)
    action = "invalidated" if event.action == "invalidate" else "corrected" if prior else "created"
    connection.execute(changes.insert().values(patient_id=patient_id, evidence_id=evidence_id,
        action=action, received=received, related_obligations=affected))
    return {"status": action, "evidence_id": evidence_id}


def materialize(connection, row):
    if not connection.execute(select(registry.c.id).where(registry.c.id == row["id"])).scalar_one_or_none():
        connection.execute(registry.insert().values(**row))


def reconsider_workflow(connection, service, context, original):
    patient_id = context.patient_id
    affected = []
    items = service.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id)
    for item in items:
        rule = service.find(connection, db.rules, item["rule_key"], required=True)["definition"]
        if item["source_id"] == original["id"] or any(code_matches(original, rule[key]) for key in ("trigger", "closure")):
            affected.append(item["id"])
    if affected:
        connection.execute(db.tasks.update().where(
            db.tasks.c.obligation_id.in_(affected), db.tasks.c.status == "pending").values(status="superseded"))
    service.reconsider_closures(connection, context.role, patient_id, [original])
    before = {item["id"]: item["status"] for item in items}
    for item in service.rows(connection, db.obligations, db.obligations.c.patient_id == patient_id):
        if item["id"] not in affected and before[item["id"]] != item["status"]:
            affected.append(item["id"])
    service.audit(connection, context.role, "clinical_evidence_reassessment", patient_id,
                  refs=[service.ref(original)], related_obligations=affected)
    return affected


def workflow_corrections(connection, patient_id):
    scope = workflow_scope(connection, patient_id)
    return set(connection.execute(select(registry.c.resource_id).where(registry.c.patient_id == patient_id,
        registry.c.source == "workflow", registry.c.scope == scope, registry.c.version > 1)).scalars())
