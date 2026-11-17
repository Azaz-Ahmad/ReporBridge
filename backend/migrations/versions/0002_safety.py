"""Persist initial stages, type dependencies and retain closure attempts."""
from datetime import UTC, datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s"}
PRE = "preconception-follow-up@1.0.0"
PREG = "pregnancy-coordination@1.0.0"
KIND = "requires_verified_closure"


def upgrade():
    bind = op.get_bind()
    old_closure_key = ("closure_evidence_obligation_id_evidence_id_key" if bind.dialect.name == "postgresql"
                       else "uq_closure_evidence_obligation_id_evidence_id")
    with op.batch_alter_table("closure_evidence", naming_convention=CONVENTION) as batch:
        batch.drop_constraint(old_closure_key, type_="unique")
        batch.create_unique_constraint("uq_closure_approval_evidence", ["approval_id", "evidence_id"])
    with op.batch_alter_table("life_stage_events") as batch:
        batch.alter_column("evidence_id", existing_type=sa.String(120), nullable=True)
        batch.create_unique_constraint("uq_life_stage_patient_stage", ["patient_id", "stage"])
    op.create_index("uq_obligation_patient_rule", "clinical_obligations", ["patient_id", "rule_key"], unique=True)
    op.add_column("obligation_dependencies", sa.Column("kind", sa.String(), server_default=KIND, nullable=False))

    metadata = sa.MetaData()
    patients, events, obligations, edges, audit = [
        sa.Table(name, metadata, autoload_with=bind) for name in
        ("patients", "life_stage_events", "clinical_obligations", "obligation_dependencies", "audit_events")
    ]
    for patient_id in bind.execute(sa.select(patients.c.id)).scalars().all():
        imported = bind.execute(sa.select(audit.c.recorded).where(
            audit.c.patient_id == patient_id, audit.c.action == "resource_imported"
        ).order_by(audit.c.sequence).limit(1)).scalar_one_or_none()
        if imported is None:
            raise RuntimeError("Cannot establish initial life-stage provenance for a legacy patient.")
        bind.execute(events.insert().values(id=uuid4().hex, patient_id=patient_id, stage="preconception",
                                            recorded=imported))
        items = {row["rule_key"]: row for row in bind.execute(sa.select(obligations).where(
            obligations.c.patient_id == patient_id)).mappings()}
        if PRE in items and PREG in items:
            prior, later = items[PRE], items[PREG]
            linked = bind.execute(sa.select(edges.c.id).where(
                edges.c.obligation_id == later["id"], edges.c.depends_on == prior["id"])).scalar_one_or_none()
            if linked is None:
                bind.execute(edges.insert().values(id=uuid4().hex, obligation_id=later["id"],
                    depends_on=prior["id"], rule_key=PREG, kind=KIND))
                bind.execute(audit.insert().values(recorded=datetime.now(UTC).isoformat(), actor="migration",
                    action="dependency_linked", patient_id=patient_id, obligation_id=later["id"], rule_key=PREG,
                    evidence_refs=[f"Observation/{later['source_id']}", f"Observation/{prior['source_id']}"],
                    detail={"depends_on": prior["id"], "kind": KIND}))
        for item in items.values():
            if item["status"] != "closed":
                continue
            bind.execute(obligations.update().where(obligations.c.id == item["id"]).values(status="open"))
            bind.execute(audit.insert().values(recorded=datetime.now(UTC).isoformat(), actor="migration",
                action="closure_reopened", patient_id=patient_id, obligation_id=item["id"], rule_key=item["rule_key"],
                evidence_refs=[f"Observation/{item['source_id']}"],
                detail={"reason": "Legacy closure requires verification under v0.2 authorization."}))


def downgrade():
    raise RuntimeError("Restore the pre-upgrade backup to roll back this safety migration.")
