"""Authorize exact patient scopes from the authenticated server role."""
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.clinical.schema_v1 import access_log, grants, identities


def now():
    return datetime.now(UTC).isoformat()


def fail(status, code, message):
    raise HTTPException(status, detail={"code": code, "message": message})


def provision(connection, patient_id):
    roles = ("coordinator", "reviewer", "viewer") if patient_id == "demo-amira" else ("coordinator",)
    existing = connection.execute(select(grants.c.role).where(grants.c.patient_id == patient_id)).scalars().all()
    for role in roles:
        if role not in existing:
            connection.execute(grants.insert().values(patient_id=patient_id, role=role))


def permitted(connection, role):
    return set(connection.execute(select(grants.c.patient_id).where(grants.c.role == role)).scalars())


@dataclass(frozen=True, slots=True)
class PatientAccess:
    """Created by trusted server code. Excluded from tool argument schemas."""
    role: str
    patient_id: str


def authorize(connection, role, patient_id):
    if not connection.execute(select(grants.c.patient_id).where(
            grants.c.role == role, grants.c.patient_id == patient_id)).scalar_one_or_none():
        fail(404, "patient_unavailable", "Patient is unavailable in this authorization scope.")
    return PatientAccess(role, patient_id)


def audit_access(connection, context, action, outcome="ok"):
    connection.execute(access_log.insert().values(patient_id=context.patient_id, actor=context.role,
        action=action, outcome=outcome, received=now()))


def claim(connection, context, namespace, external_id):
    patients = matching_claims(connection, namespace, external_id)
    if context.patient_id not in patients:
        connection.execute(identities.insert().values(namespace=namespace, external_id=external_id,
            patient_id=context.patient_id, actor=context.role, received=now()))
        audit_access(connection, context, "identity_claimed")
        patients.add(context.patient_id)
    return "ambiguous" if len(patients) > 1 else "mapped"


def matching_claims(connection, namespace, external_id):
    return set(connection.execute(select(identities.c.patient_id).where(
        identities.c.namespace == namespace, identities.c.external_id == external_id)).scalars())


def resolve(connection, context, namespace, external_id):
    patients = matching_claims(connection, namespace, external_id)
    if context.patient_id not in patients:
        fail(404, "identity_not_found", "No external identity matched this patient scope.")
    if len(patients) != 1:
        fail(409, "ambiguous_identity", "External identity needs authorized review.")
    return context.patient_id
