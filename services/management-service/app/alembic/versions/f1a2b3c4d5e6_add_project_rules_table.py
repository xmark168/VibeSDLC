"""Add project_rules table for knowledge base

Revision ID: f1a2b3c4d5e6
Revises: 1a31ce608336
Create Date: 2025-10-28 15:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    # Create project_rules table
    op.create_table(
        'project_rules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tags', JSONB, nullable=False, server_default='[]'),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('source_blocker_id', sa.String(length=100), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='daily_blocker'),
        sa.Column('created_by', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('applied_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('effectiveness_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_project_rules_project_id', 'project_rules', ['project_id'])
    op.create_index('ix_project_rules_is_active', 'project_rules', ['is_active'], postgresql_where=sa.text('is_active = true'))
    op.create_index('ix_project_rules_tags', 'project_rules', ['tags'], postgresql_using='gin')
    op.create_index('ix_project_rules_category', 'project_rules', ['category'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_project_rules_category', table_name='project_rules')
    op.drop_index('ix_project_rules_tags', table_name='project_rules', postgresql_using='gin')
    op.drop_index('ix_project_rules_is_active', table_name='project_rules')
    op.drop_index('ix_project_rules_project_id', table_name='project_rules')
    
    # Drop table
    op.drop_table('project_rules')

