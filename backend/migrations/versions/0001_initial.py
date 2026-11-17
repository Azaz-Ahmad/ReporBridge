"""Initial ReproBridge workflow schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('clinical_pathways',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('label', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('patients',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('resource', sa.JSON(), nullable=False),
    sa.Column('stage', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('clinical_evidence',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('patient_id', sa.String(length=120), nullable=False),
    sa.Column('resource', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rule_versions',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('rule_id', sa.String(), nullable=False),
    sa.Column('version', sa.String(), nullable=False),
    sa.Column('pathway_id', sa.String(length=120), nullable=False),
    sa.Column('definition', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['pathway_id'], ['clinical_pathways.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rule_id', 'version')
    )
    op.create_table('clinical_obligations',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('patient_id', sa.String(length=120), nullable=False),
    sa.Column('rule_key', sa.String(length=120), nullable=False),
    sa.Column('source_id', sa.String(length=120), nullable=False),
    sa.Column('owner', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('created', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['rule_key'], ['rule_versions.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['clinical_evidence.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('patient_id', 'rule_key', 'source_id')
    )
    op.create_table('life_stage_events',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('patient_id', sa.String(length=120), nullable=False),
    sa.Column('stage', sa.String(), nullable=False),
    sa.Column('recorded', sa.String(), nullable=False),
    sa.Column('evidence_id', sa.String(length=120), nullable=False),
    sa.ForeignKeyConstraint(['evidence_id'], ['clinical_evidence.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('agent_executions',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('obligation_id', sa.String(length=120), nullable=False),
    sa.Column('actor', sa.String(), nullable=False),
    sa.Column('recorded', sa.String(), nullable=False),
    sa.Column('result', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['obligation_id'], ['clinical_obligations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('audit_events',
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('recorded', sa.String(), nullable=False),
    sa.Column('actor', sa.String(), nullable=False),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('patient_id', sa.String(length=120), nullable=False),
    sa.Column('obligation_id', sa.String(length=120), nullable=True),
    sa.Column('rule_key', sa.String(), nullable=False),
    sa.Column('evidence_refs', sa.JSON(), nullable=False),
    sa.Column('detail', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['obligation_id'], ['clinical_obligations.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('sequence')
    )
    op.create_table('obligation_dependencies',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('obligation_id', sa.String(length=120), nullable=False),
    sa.Column('depends_on', sa.String(length=120), nullable=False),
    sa.Column('rule_key', sa.String(length=120), nullable=False),
    sa.ForeignKeyConstraint(['depends_on'], ['clinical_obligations.id'], ),
    sa.ForeignKeyConstraint(['obligation_id'], ['clinical_obligations.id'], ),
    sa.ForeignKeyConstraint(['rule_key'], ['rule_versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('obligation_id', 'depends_on')
    )
    op.create_table('care_coordination_tasks',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('obligation_id', sa.String(length=120), nullable=False),
    sa.Column('execution_id', sa.String(length=120), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('action', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['execution_id'], ['agent_executions.id'], ),
    sa.ForeignKeyConstraint(['obligation_id'], ['clinical_obligations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('clinical_approvals',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('task_id', sa.String(length=120), nullable=False),
    sa.Column('obligation_id', sa.String(length=120), nullable=False),
    sa.Column('decision', sa.String(), nullable=False),
    sa.Column('actor', sa.String(), nullable=False),
    sa.Column('recorded', sa.String(), nullable=False),
    sa.Column('evidence_refs', sa.JSON(), nullable=False),
    sa.Column('note', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['obligation_id'], ['clinical_obligations.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['care_coordination_tasks.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_id')
    )
    op.create_table('closure_evidence',
    sa.Column('id', sa.String(length=120), nullable=False),
    sa.Column('obligation_id', sa.String(length=120), nullable=False),
    sa.Column('evidence_id', sa.String(length=120), nullable=False),
    sa.Column('approval_id', sa.String(length=120), nullable=False),
    sa.Column('recorded', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['approval_id'], ['clinical_approvals.id'], ),
    sa.ForeignKeyConstraint(['evidence_id'], ['clinical_evidence.id'], ),
    sa.ForeignKeyConstraint(['obligation_id'], ['clinical_obligations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('obligation_id', 'evidence_id')
    )


def downgrade():
    op.drop_table('closure_evidence')
    op.drop_table('clinical_approvals')
    op.drop_table('care_coordination_tasks')
    op.drop_table('obligation_dependencies')
    op.drop_table('audit_events')
    op.drop_table('agent_executions')
    op.drop_table('life_stage_events')
    op.drop_table('clinical_obligations')
    op.drop_table('rule_versions')
    op.drop_table('clinical_evidence')
    op.drop_table('patients')
    op.drop_table('clinical_pathways')
