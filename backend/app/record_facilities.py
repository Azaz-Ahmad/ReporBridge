"""Additive evidence annotations; patient grants and immutable clinical payloads stay unchanged."""
import sqlalchemy as sa
from app.clinical.access import authorize, fail, now
meta = sa.MetaData()
facilities = sa.Table("clinical_record_facilities", meta,
    sa.Column("patient_id",sa.String(120),primary_key=True),
    sa.Column("evidence_id",sa.String(120),primary_key=True),
    sa.Column("facility",sa.String(120),nullable=False),
    sa.Column("receiving_facility",sa.String(120),nullable=True),
    sa.Column("received",sa.String,nullable=False),
    sa.Column("simulation",sa.Boolean,nullable=False),sa.Column("actor",sa.String,nullable=False))


def assign(connection, actor, patient_id, evidence_id, facility, receiving="Hospital B"):
    authorize(connection,actor,patient_id)
    from app.clinical.gateway import ClinicalRetrieval
    source=ClinicalRetrieval(connection,authorize(connection,actor,patient_id)).get(evidence_id=evidence_id).evidence
    existing=connection.execute(sa.select(facilities).where(facilities.c.patient_id==patient_id,facilities.c.evidence_id==evidence_id)).mappings().first()
    if existing:
        if existing["facility"]!=facility or existing["receiving_facility"]!=receiving:
            fail(409,"immutable_facility","Source facility annotations cannot be silently reassigned.")
        return dict(existing)
    row=dict(patient_id=patient_id,evidence_id=evidence_id,facility=facility,receiving_facility=receiving,
             received=source.received,simulation=True,actor=actor)
    connection.execute(facilities.insert().values(**row))
    return row


def provenance(connection,row):
    annotation=connection.execute(sa.select(facilities).where(facilities.c.patient_id==row["patient_id"],facilities.c.evidence_id==row["id"])).mappings().first()
    if not annotation:return {}
    return {"facility":{"simulation":annotation["simulation"],"origin":annotation["facility"],
        "receiving":annotation["receiving_facility"],"received_at":annotation["received"],"transport":"received via simulated provider exchange"}}
