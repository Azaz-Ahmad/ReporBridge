"""Add patient-scoped facility attributes without changing M08 resources/contracts."""
from alembic import op
from app.record_facilities import meta
revision="0009"
down_revision="0008"
branch_labels=None
depends_on=None

def upgrade():
    meta.create_all(op.get_bind())

def downgrade():
    raise RuntimeError("Restore a backup to preserve source provenance.")
