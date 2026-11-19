"""Add prevention decisions and their independent timing/reviewer history."""
from alembic import op
from app.prevention.schema_v1 import meta

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    meta.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Restore the pre-upgrade backup to preserve decision history.")
