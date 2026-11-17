"""Add clinical data storage and explicit patient grants."""
from alembic import op
import sqlalchemy as sa
from app.clinical.schema_v1 import grants, meta

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    meta.create_all(bind)
    for patient_id in bind.execute(sa.text("SELECT id FROM patients")).scalars().all():
        roles = ("coordinator", "reviewer", "viewer") if patient_id == "demo-amira" else ("coordinator",)
        bind.execute(grants.insert(), [dict(patient_id=patient_id, role=role) for role in roles])
    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX ix_clinical_chunks_fts ON clinical_document_chunks "
                   "USING gin (to_tsvector('simple', body))")


def downgrade():
    raise RuntimeError("Restore the pre-upgrade backup to preserve clinical evidence history.")
