import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import JSON, Column, ForeignKey, Integer, MetaData, String, Table, UniqueConstraint, create_engine, event

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
url = os.getenv("DATABASE_URL") or f"sqlite:///{(ROOT / 'demo.db').as_posix()}"
engine = create_engine(url, pool_pre_ping=True)
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

metadata = MetaData()


def key(name="id"):
    return Column(name, String(120), primary_key=True)


def string(name):
    return Column(name, String, nullable=False)


def data(name):
    return Column(name, JSON, nullable=False)


def fk(name, target):
    return Column(name, String(120), ForeignKey(target), nullable=False)


patients = Table("patients", metadata, key(), data("resource"), string("stage"))
evidence = Table("clinical_evidence", metadata, key(), fk("patient_id", "patients.id"), data("resource"))
events = Table("life_stage_events", metadata, key(), fk("patient_id", "patients.id"), string("stage"),
               string("recorded"), fk("evidence_id", "clinical_evidence.id"))
pathways = Table("clinical_pathways", metadata, key(), string("label"))
rules = Table("rule_versions", metadata, key(), string("rule_id"), string("version"),
              fk("pathway_id", "clinical_pathways.id"), data("definition"), UniqueConstraint("rule_id", "version"))
obligations = Table("clinical_obligations", metadata, key(), fk("patient_id", "patients.id"),
                    fk("rule_key", "rule_versions.id"), fk("source_id", "clinical_evidence.id"),
                    string("owner"), string("status"), string("created"),
                    UniqueConstraint("patient_id", "rule_key", "source_id"))
dependencies = Table("obligation_dependencies", metadata, key(),
                     fk("obligation_id", "clinical_obligations.id"), fk("depends_on", "clinical_obligations.id"),
                     fk("rule_key", "rule_versions.id"), UniqueConstraint("obligation_id", "depends_on"))
executions = Table("agent_executions", metadata, key(), fk("obligation_id", "clinical_obligations.id"),
                   string("actor"), string("recorded"), data("result"))
tasks = Table("care_coordination_tasks", metadata, key(), fk("obligation_id", "clinical_obligations.id"),
              fk("execution_id", "agent_executions.id"), string("status"), string("action"))
approvals = Table("clinical_approvals", metadata, key(), fk("task_id", "care_coordination_tasks.id"),
                  fk("obligation_id", "clinical_obligations.id"), string("decision"), string("actor"),
                  string("recorded"), data("evidence_refs"), string("note"), UniqueConstraint("task_id"))
closures = Table("closure_evidence", metadata, key(), fk("obligation_id", "clinical_obligations.id"),
                 fk("evidence_id", "clinical_evidence.id"), fk("approval_id", "clinical_approvals.id"),
                 string("recorded"), UniqueConstraint("obligation_id", "evidence_id"))
audit = Table("audit_events", metadata, Column("sequence", Integer, primary_key=True),
              string("recorded"), string("actor"), string("action"), fk("patient_id", "patients.id"),
              Column("obligation_id", String(120), ForeignKey("clinical_obligations.id")),
              string("rule_key"), data("evidence_refs"), data("detail"))
