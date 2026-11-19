"""Isolated demo-session calendar dates; no system-time mutation."""
from alembic import op
from app.prevention.tsp_schema import meta
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    meta.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Restore a backup to preserve demo-session history.")
