"""Rename backlog_items table to stories

Revision ID: 0b0f13415291
Revises: 342f2a25b41b
Create Date: 2025-11-16 22:05:39.187426

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '0b0f13415291'
down_revision = '342f2a25b41b'
branch_labels = None
depends_on = None


def upgrade():
    # Rename table from backlog_items to stories
    op.rename_table('backlog_items', 'stories')


def downgrade():
    # Rename table back from stories to backlog_items
    op.rename_table('stories', 'backlog_items')
