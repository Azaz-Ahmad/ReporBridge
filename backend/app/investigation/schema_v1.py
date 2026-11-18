"""Frozen Sprint 2 persistence for migration 0005."""
import sqlalchemy as sa

meta = sa.MetaData()
runs = sa.Table("clinical_investigation_runs", meta,
    sa.Column("id", sa.String(120), primary_key=True),
    sa.Column("patient_id", sa.String(120), nullable=False, index=True),
    sa.Column("actor", sa.String(40), nullable=False),
    sa.Column("request_id", sa.String(100), nullable=False),
    sa.Column("fingerprint", sa.String(64), nullable=False),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("created", sa.String(60), nullable=False),
    sa.Column("updated", sa.String(60), nullable=False),
    sa.Column("detail", sa.JSON, nullable=False),
    sa.UniqueConstraint("patient_id", "actor", "request_id", name="uq_investigation_request"))
reviews = sa.Table("clinical_investigation_reviews", meta,
    sa.Column("run_id", sa.String(120), sa.ForeignKey("clinical_investigation_runs.id"), primary_key=True),
    sa.Column("actor", sa.String(40), nullable=False),
    sa.Column("recorded", sa.String(60), nullable=False),
    sa.Column("decision", sa.String(40), nullable=False),
    sa.Column("note", sa.String(500), nullable=False))
