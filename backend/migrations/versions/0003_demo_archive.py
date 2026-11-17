"""Keep completed Amira demo runs in a separate audit archive."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "demo_run_archive",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("patient_id", sa.String(120), nullable=False),
        sa.Column("recorded", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("audit_count", sa.Integer(), nullable=False),
        sa.Column("records", sa.JSON(), nullable=False),
    )


def downgrade():
    raise RuntimeError("Restore the pre-upgrade backup to retain demo run archives.")
