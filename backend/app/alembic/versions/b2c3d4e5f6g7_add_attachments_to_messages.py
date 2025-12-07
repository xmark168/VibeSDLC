"""add attachments to messages

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-07 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add attachments column to messages table (JSON array for file metadata)
    op.add_column('messages', sa.Column('attachments', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('messages', 'attachments')
