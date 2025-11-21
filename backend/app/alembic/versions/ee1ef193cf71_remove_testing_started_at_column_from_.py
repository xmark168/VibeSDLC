"""Remove testing_started_at column from stories

Revision ID: ee1ef193cf71
Revises: d1886f6a9d64
Create Date: 2025-11-21 17:56:20.504985

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ee1ef193cf71'
down_revision = 'd1886f6a9d64'
branch_labels = None
depends_on = None


def upgrade():
    # Remove testing_started_at column from stories table
    op.drop_column('stories', 'testing_started_at')


def downgrade():
    # Add testing_started_at column back to stories table
    op.add_column('stories', sa.Column('testing_started_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
