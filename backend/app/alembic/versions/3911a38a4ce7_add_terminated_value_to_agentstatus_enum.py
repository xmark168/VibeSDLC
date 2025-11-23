"""Add terminated value to agentstatus enum

Revision ID: 3911a38a4ce7
Revises: 202511220001
Create Date: 2025-11-23 09:16:13.505434

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '3911a38a4ce7'
down_revision = '202511220001'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'terminated' value to agentstatus enum
    # Note: PostgreSQL doesn't allow ALTER TYPE in transaction blocks,
    # so we need to execute this outside of a transaction
    op.execute("COMMIT")  # Commit any pending transaction
    op.execute("ALTER TYPE agentstatus ADD VALUE IF NOT EXISTS 'terminated'")


def downgrade():
    # PostgreSQL doesn't support removing enum values directly
    # The only way is to recreate the enum, which is risky
    # So we'll just pass - this migration is not reversible
    pass
