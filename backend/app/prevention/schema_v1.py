"""Frozen prevention domain for migration 0006. Historical identifiers survive demo reset."""
import sqlalchemy as sa

meta = sa.MetaData()


def text(name, nullable=False, **kwargs):
    return sa.Column(name, sa.String, nullable=nullable, **kwargs)


policies = sa.Table("prevention_timing_policies", meta,
    text("id", primary_key=True), text("version"), text("source"), text("status"),
    sa.Column("definition", sa.JSON, nullable=False), text("created"), text("actor"))
decisions = sa.Table("prevention_decisions", meta,
    text("id", primary_key=True), text("patient_id", index=True), text("obligation_id", index=True),
    text("purpose"), text("rationale"), text("owner"), text("rule_key"),
    text("status"), text("policy_id", nullable=True), text("due_date", nullable=True),
    sa.Column("source_refs", sa.JSON, nullable=False),
    sa.Column("snapshot", sa.JSON, nullable=False), text("snapshot_hash"),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("archived", sa.Boolean, nullable=False),
    text("created"), text("updated"), text("last_investigation_id", nullable=True))
prerequisites = sa.Table("prevention_prerequisites", meta,
    text("id", primary_key=True), text("decision_id", index=True),
    text("category"), text("rule_key"), sa.Column("definition", sa.JSON, nullable=False),
    text("status"), sa.Column("source_refs", sa.JSON, nullable=False),
    sa.Column("issues", sa.JSON, nullable=False), text("evaluated"))
records = sa.Table("prevention_decision_records", meta,
    text("id", primary_key=True), text("decision_id", unique=True), text("patient_id"),
    text("actor"), text("outcome"), text("rationale"), text("recorded"),
    sa.Column("source_refs", sa.JSON, nullable=False), text("rule_key"), text("policy_id", nullable=True),
    sa.Column("snapshot", sa.JSON, nullable=False), sa.Column("follow_up", sa.JSON, nullable=False))
audit = sa.Table("prevention_decision_audit", meta,
    sa.Column("sequence", sa.Integer, primary_key=True), text("decision_id", index=True),
    text("patient_id", index=True), text("actor"), text("action"), text("recorded"),
    sa.Column("detail", sa.JSON, nullable=False))
