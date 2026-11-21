"""Additive, non-actionable candidates; deliberately separate from active care obligations."""
import sqlalchemy as sa
meta = sa.MetaData()
candidates = sa.Table("historical_obligation_candidates", meta,
    sa.Column("id",sa.String(100),primary_key=True),
    sa.Column("patient_id",sa.String(100),nullable=False,index=True),
    sa.Column("transition_id",sa.String(100),nullable=False),
    sa.Column("rule_id",sa.String(100),nullable=False),sa.Column("rule_version",sa.String(40),nullable=False),
    sa.Column("title",sa.String,nullable=False),sa.Column("owner_role",sa.String(80),nullable=False),
    sa.Column("status",sa.String(40),nullable=False),sa.Column("created",sa.String,nullable=False),
    sa.Column("demo_date",sa.String,nullable=False),sa.Column("updated",sa.String,nullable=False),
    sa.Column("rule_snapshot",sa.JSON,nullable=False),sa.Column("source_refs",sa.JSON,nullable=False),
    sa.Column("window_snapshot",sa.JSON,nullable=False),sa.Column("decision",sa.JSON,nullable=True),
    sa.Column("obligation_id",sa.String(100),nullable=True),sa.Column("confirmation_resource",sa.JSON,nullable=True),
    sa.Column("archived",sa.Boolean,nullable=False),
    sa.UniqueConstraint("patient_id","transition_id","rule_id","rule_version",name="uq_historical_candidate_transition_rule"))
