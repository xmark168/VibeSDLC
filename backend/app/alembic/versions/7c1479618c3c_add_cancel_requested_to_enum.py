"""add_cancel_requested_to_enum

Revision ID: 7c1479618c3c
Revises: ece22f8ec0f3
Create Date: 2025-12-14 15:35:47.673133

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '7c1479618c3c'
down_revision = 'ece22f8ec0f3'
branch_labels = None
depends_on = None


def upgrade():
    # Add CANCEL_REQUESTED value to storyagentstate enum if it doesn't exist
    op.execute("ALTER TYPE storyagentstate ADD VALUE IF NOT EXISTS 'CANCEL_REQUESTED'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # If you need to remove this, you would need to recreate the enum type
    pass
