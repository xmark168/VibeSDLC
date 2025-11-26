"""add_token_budget_fields_to_projects

Revision ID: a1b2c3d4e5f6
Revises: 295066f08645
Create Date: 2025-11-26 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '295066f08645'
branch_labels = None
depends_on = None


def upgrade():
    """Add token budget fields to projects table for cost control."""
    # Add token budget columns to projects table
    op.add_column('projects', sa.Column('token_budget_daily', sa.Integer(), nullable=False, server_default='100000'))
    op.add_column('projects', sa.Column('token_budget_monthly', sa.Integer(), nullable=False, server_default='2000000'))
    op.add_column('projects', sa.Column('tokens_used_today', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('tokens_used_this_month', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('budget_last_reset_daily', sa.DateTime(), nullable=True))
    op.add_column('projects', sa.Column('budget_last_reset_monthly', sa.DateTime(), nullable=True))


def downgrade():
    """Remove token budget fields from projects table."""
    op.drop_column('projects', 'budget_last_reset_monthly')
    op.drop_column('projects', 'budget_last_reset_daily')
    op.drop_column('projects', 'tokens_used_this_month')
    op.drop_column('projects', 'tokens_used_today')
    op.drop_column('projects', 'token_budget_monthly')
    op.drop_column('projects', 'token_budget_daily')
