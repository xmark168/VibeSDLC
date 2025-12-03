"""merge_heads

Revision ID: 8e2afa406019
Revises: a1b2c3d4e5f6, ca171d6b07a4
Create Date: 2025-12-03 22:57:12.057468

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '8e2afa406019'
down_revision = ('a1b2c3d4e5f6', 'ca171d6b07a4')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
