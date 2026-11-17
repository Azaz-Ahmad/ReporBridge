"""Frozen M08 table definitions for revision 0004."""
import sqlalchemy as sa

meta = sa.MetaData()


def field(name, *constraints, size=120, nullable=False, **kwargs):
    return sa.Column(name, sa.String(size), *constraints, nullable=nullable, **kwargs)


grants = sa.Table("clinical_patient_grants", meta,
    field("patient_id", primary_key=True), field("role", primary_key=True))
identities = sa.Table("clinical_identity_claims", meta,
    field("namespace", primary_key=True), field("external_id", primary_key=True),
    field("patient_id", primary_key=True), field("actor"), field("received"))
registry = sa.Table("clinical_evidence_versions", meta,
    field("id", primary_key=True), field("patient_id"), field("source"), field("scope"),
    field("kind"), field("resource_id"), sa.Column("version", sa.Integer, nullable=False),
    field("event_time", nullable=True), field("received"), field("clinical_time", nullable=True),
    field("status"), field("digest", size=64), field("actor"),
    field("supersedes", sa.ForeignKey("clinical_evidence_versions.id"), nullable=True),
    sa.Column("resource", sa.JSON, nullable=False), sa.Column("normalized", sa.JSON, nullable=False),
    sa.UniqueConstraint("patient_id", "source", "scope", "kind", "resource_id", "version"),
    sa.Index("ix_clinical_evidence_patient_kind", "patient_id", "kind", "resource_id"),
    sa.Index("ix_clinical_evidence_predecessor", "supersedes"))
chunks = sa.Table("clinical_document_chunks", meta,
    field("evidence_id", sa.ForeignKey("clinical_evidence_versions.id"), primary_key=True),
    sa.Column("position", sa.Integer, primary_key=True), field("section", size=160),
    sa.Column("body", sa.Text, nullable=False))
receipts = sa.Table("clinical_event_receipts", meta,
    field("source", primary_key=True), field("event_id", primary_key=True),
    field("patient_id", primary_key=True), field("digest", size=64), field("event_time"), field("received"),
    field("evidence_id", sa.ForeignKey("clinical_evidence_versions.id")), field("actor"),
    sa.Index("ix_clinical_receipt_evidence", "evidence_id"))
changes = sa.Table("clinical_change_outbox", meta,
    sa.Column("sequence", sa.Integer, primary_key=True), field("patient_id"),
    field("evidence_id", sa.ForeignKey("clinical_evidence_versions.id")),
    field("action"), field("received"), sa.Column("related_obligations", sa.JSON, nullable=False),
    sa.Index("ix_clinical_changes_patient", "patient_id", "sequence"))
access_log = sa.Table("clinical_access_audit", meta,
    sa.Column("sequence", sa.Integer, primary_key=True), field("patient_id"), field("actor"),
    field("action"), field("received"), field("outcome"))
