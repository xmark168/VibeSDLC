"""add_lean_kanban_features

Revision ID: d1886f6a9d64
Revises: 88c7e8f763e3
Create Date: 2025-11-18 20:21:53.342363

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'd1886f6a9d64'
down_revision = '88c7e8f763e3'
branch_labels = None
depends_on = None


def upgrade():
    # Add flow tracking timestamps to stories table
    op.add_column('stories', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('stories', sa.Column('review_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('stories', sa.Column('testing_started_at', sa.DateTime(timezone=True), nullable=True))

    # Create column_wip_limits table
    op.create_table(
        'column_wip_limits',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('column_name', sa.String(50), nullable=False),
        sa.Column('wip_limit', sa.Integer(), nullable=False),
        sa.Column('limit_type', sa.String(10), nullable=False, server_default='hard'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'column_name', name='uq_project_column_wip')
    )
    op.create_index('ix_wip_limits_project', 'column_wip_limits', ['project_id'])

    # Create workflow_policies table
    op.create_table(
        'workflow_policies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('from_status', sa.String(50), nullable=False),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('criteria', sa.JSON(), nullable=True),
        sa.Column('required_role', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'from_status', 'to_status', name='uq_project_workflow')
    )
    op.create_index('ix_policies_project', 'workflow_policies', ['project_id'])

    # Create default WIP limits for existing projects
    # InProgress: 3, Review: 2, Testing: 2, Done: unlimited
    op.execute("""
        INSERT INTO column_wip_limits (id, created_at, updated_at, project_id, column_name, wip_limit, limit_type)
        SELECT
            gen_random_uuid(),
            NOW(),
            NOW(),
            p.id,
            'InProgress',
            3,
            'hard'
        FROM projects p
    """)

    op.execute("""
        INSERT INTO column_wip_limits (id, created_at, updated_at, project_id, column_name, wip_limit, limit_type)
        SELECT
            gen_random_uuid(),
            NOW(),
            NOW(),
            p.id,
            'Review',
            2,
            'hard'
        FROM projects p
    """)

    # Create default workflow policies for existing projects
    # Todo -> InProgress: requires assignee
    op.execute("""
        INSERT INTO workflow_policies (id, created_at, updated_at, project_id, from_status, to_status, criteria, is_active)
        SELECT
            gen_random_uuid(),
            NOW(),
            NOW(),
            p.id,
            'Todo',
            'InProgress',
            '{"assignee_required": true}'::json,
            true
        FROM projects p
    """)

    # InProgress -> Review: no blockers
    op.execute("""
        INSERT INTO workflow_policies (id, created_at, updated_at, project_id, from_status, to_status, criteria, is_active)
        SELECT
            gen_random_uuid(),
            NOW(),
            NOW(),
            p.id,
            'InProgress',
            'Review',
            '{"no_blockers": true}'::json,
            true
        FROM projects p
    """)


def downgrade():
    # Drop tables
    op.drop_index('ix_policies_project', table_name='workflow_policies')
    op.drop_table('workflow_policies')

    op.drop_index('ix_wip_limits_project', table_name='column_wip_limits')
    op.drop_table('column_wip_limits')

    # Remove flow tracking columns from stories
    op.drop_column('stories', 'testing_started_at')
    op.drop_column('stories', 'review_started_at')
    op.drop_column('stories', 'started_at')
