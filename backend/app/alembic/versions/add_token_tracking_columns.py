"""add token tracking columns to agents

Revision ID: add_token_tracking
Revises: drop_workflow_policies
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_token_tracking'
down_revision = 'drop_workflow_policies'
branch_labels = None
depends_on = None


def upgrade():
    # Add token tracking columns to agents table
    op.add_column('agents', sa.Column('tokens_used_total', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('agents', sa.Column('tokens_used_today', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('agents', sa.Column('llm_calls_total', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('agents', 'llm_calls_total')
    op.drop_column('agents', 'tokens_used_today')
    op.drop_column('agents', 'tokens_used_total')
