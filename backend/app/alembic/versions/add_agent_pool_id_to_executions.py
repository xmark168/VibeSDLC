"""add agent_id and pool_id to agent_executions

Revision ID: add_agent_pool_id_exec
Revises: add_token_tracking
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_agent_pool_id_exec'
down_revision = 'add_token_tracking'
branch_labels = None
depends_on = None


def upgrade():
    # Add agent_id column
    op.add_column('agent_executions', sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('ix_agent_executions_agent_id', 'agent_executions', ['agent_id'])
    op.create_foreign_key(
        'fk_agent_executions_agent_id',
        'agent_executions', 'agents',
        ['agent_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add pool_id column
    op.add_column('agent_executions', sa.Column('pool_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('ix_agent_executions_pool_id', 'agent_executions', ['pool_id'])
    op.create_foreign_key(
        'fk_agent_executions_pool_id',
        'agent_executions', 'agent_pools',
        ['pool_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_agent_executions_pool_id', 'agent_executions', type_='foreignkey')
    op.drop_index('ix_agent_executions_pool_id', 'agent_executions')
    op.drop_column('agent_executions', 'pool_id')
    
    op.drop_constraint('fk_agent_executions_agent_id', 'agent_executions', type_='foreignkey')
    op.drop_index('ix_agent_executions_agent_id', 'agent_executions')
    op.drop_column('agent_executions', 'agent_id')
