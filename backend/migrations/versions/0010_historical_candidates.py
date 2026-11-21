"""Add non-actionable historical candidates without altering existing clinical tables or rules."""
from alembic import op
from app.historical_candidates_schema import meta
revision="0010"
down_revision="0009"
branch_labels=None
depends_on=None
def upgrade():meta.create_all(op.get_bind())
def downgrade():raise RuntimeError("Restore a backup to preserve candidate review history.")
