"""Bounded model transport inspection, separate from clinical state."""
from alembic import op
from app.model_payload_schema import meta
revision="0011"
down_revision="0010"
branch_labels=None
depends_on=None
def upgrade():meta.create_all(op.get_bind())
def downgrade():raise RuntimeError("Restore a backup to preserve model audit history.")
