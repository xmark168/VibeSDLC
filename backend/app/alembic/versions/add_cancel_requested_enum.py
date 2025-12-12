"""add cancel_requested to storyagentstate enum

Revision ID: add_cancel_requested
Revises: e091278a11be
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cancel_requested'
down_revision = 'e091278a11be'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'cancel_requested' value to storyagentstate enum
    op.execute("ALTER TYPE storyagentstate ADD VALUE IF NOT EXISTS 'cancel_requested'")


def downgrade():
    # PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the enum type without the value
    pass
