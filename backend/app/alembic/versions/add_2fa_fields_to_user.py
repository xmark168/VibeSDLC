"""Add 2FA fields to user table

Revision ID: add_2fa_fields
Revises: remove_redundant_fields
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_2fa_fields'
down_revision = 'remove_redundant_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add totp_secret column
    op.add_column('users', sa.Column('totp_secret', sa.String(), nullable=True))
    # Add backup_codes column (JSON array)
    op.add_column('users', sa.Column('backup_codes', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'backup_codes')
    op.drop_column('users', 'totp_secret')
