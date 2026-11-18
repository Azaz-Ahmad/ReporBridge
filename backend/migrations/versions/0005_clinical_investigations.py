"""Add independent LLM evidence investigation and summary review records."""
from alembic import op
from app.investigation.schema_v1 import meta

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    meta.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Restore the pre-upgrade backup to preserve investigation history.")
