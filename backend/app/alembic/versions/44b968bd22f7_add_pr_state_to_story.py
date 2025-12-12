"""add pr_state to story

Revision ID: 44b968bd22f7
Revises: add_cancel_requested
Create Date: 2025-12-12 12:49:57.289593

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = '44b968bd22f7'
down_revision = 'add_cancel_requested'
branch_labels = None
depends_on = None


def upgrade():
    # Add pr_state column to stories table
    op.add_column('stories', sa.Column('pr_state', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))


def downgrade():
    op.drop_column('stories', 'pr_state')
