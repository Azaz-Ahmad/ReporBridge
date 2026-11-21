"""Immutable model original, clinician-authored versions and version-bound review."""
from alembic import op
from app.draft_schema import meta
revision="0012"
down_revision="0011"
branch_labels=None
depends_on=None
def upgrade():meta.create_all(op.get_bind())
def downgrade():raise RuntimeError("Restore a backup to preserve clinician-authored audit history.")
