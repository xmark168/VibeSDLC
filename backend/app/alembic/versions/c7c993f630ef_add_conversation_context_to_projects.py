"""add conversation context to projects

Revision ID: c7c993f630ef
Revises: 295066f08645
Create Date: 2025-11-25 15:57:39.129050

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'c7c993f630ef'
down_revision = '295066f08645'
branch_labels = None
depends_on = None


def upgrade():
    # Add conversation context fields to projects table
    op.add_column('projects',
        sa.Column('active_agent_id', sa.UUID(), nullable=True)
    )
    op.add_column('projects',
        sa.Column('active_agent_updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_projects_active_agent',
        'projects', 'agents',
        ['active_agent_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for faster lookups
    op.create_index('ix_projects_active_agent', 'projects', ['active_agent_id'])


def downgrade():
    # Remove index
    op.drop_index('ix_projects_active_agent', 'projects')
    
    # Remove foreign key
    op.drop_constraint('fk_projects_active_agent', 'projects', type_='foreignkey')
    
    # Remove columns
    op.drop_column('projects', 'active_agent_updated_at')
    op.drop_column('projects', 'active_agent_id')
