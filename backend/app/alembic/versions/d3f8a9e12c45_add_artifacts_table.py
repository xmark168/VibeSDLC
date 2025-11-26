"""add_artifacts_table

Revision ID: d3f8a9e12c45
Revises: 5dc57d69c4b4
Create Date: 2025-11-25 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'd3f8a9e12c45'
down_revision = '5dc57d69c4b4'
branch_labels = None
depends_on = None


def upgrade():
    # Create artifacts table
    op.create_table('artifacts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=True),
        sa.Column('agent_name', sa.String(), nullable=False),
        sa.Column('artifact_type', sa.Enum(
            'PRD', 'ARCHITECTURE', 'API_SPEC', 'DATABASE_SCHEMA', 
            'USER_STORIES', 'CODE', 'TEST_PLAN', 'REVIEW', 'ANALYSIS',
            name='artifacttype'
        ), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('parent_artifact_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.Enum(
            'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'ARCHIVED',
            name='artifactstatus'
        ), nullable=False),
        sa.Column('reviewed_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_feedback', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_artifact_id'], ['artifacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_artifacts_project_id', 'artifacts', ['project_id'])
    op.create_index('ix_artifacts_project_type', 'artifacts', ['project_id', 'artifact_type'])
    op.create_index('ix_artifacts_status', 'artifacts', ['status'])
    op.create_index('ix_artifacts_agent_id', 'artifacts', ['agent_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_artifacts_agent_id', table_name='artifacts')
    op.drop_index('ix_artifacts_status', table_name='artifacts')
    op.drop_index('ix_artifacts_project_type', table_name='artifacts')
    op.drop_index('ix_artifacts_project_id', table_name='artifacts')
    
    # Drop table
    op.drop_table('artifacts')
    
    # Drop enums (PostgreSQL specific)
    op.execute('DROP TYPE IF EXISTS artifacttype')
    op.execute('DROP TYPE IF EXISTS artifactstatus')
