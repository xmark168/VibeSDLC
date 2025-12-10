"""add_paused_to_storyagentstate_enum

Revision ID: 0ed89de50ce6
Revises: da61b7fe3860
Create Date: 2025-12-10 20:31:49.653738

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '0ed89de50ce6'
down_revision = 'da61b7fe3860'
branch_labels = None
depends_on = None


def upgrade():
    # Add PAUSED value to storyagentstate enum
    op.execute("ALTER TYPE storyagentstate ADD VALUE IF NOT EXISTS 'PAUSED'")


def downgrade():
    # PostgreSQL doesn't support removing enum values easily
    # Would need to recreate the type
    pass
