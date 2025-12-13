"""add priority to agent_pools

Revision ID: add_pool_priority
Revises: add_agent_pool_id_exec
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_pool_priority'
down_revision = 'add_agent_pool_id_exec'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('agent_pools', sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_agent_pools_priority', 'agent_pools', ['priority'])


def downgrade():
    op.drop_index('ix_agent_pools_priority', 'agent_pools')
    op.drop_column('agent_pools', 'priority')
