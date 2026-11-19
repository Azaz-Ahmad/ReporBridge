"""Add the clinically unconfirmed gestational policy to the existing registry."""
from alembic import op
from app.prevention.schema_v1 import policies
from app.prevention.window import default_policy

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(policies.insert().values(id="glycemic-assessment-pregnancy", version="1",
        source="CITATION_PENDING_CLINICAL_CONFIRMATION", status="active", definition=default_policy(),
        created="2026-11-01T00:00:00+00:00", actor="migration"))


def downgrade():
    raise RuntimeError("Restore a backup to preserve policy history.")
