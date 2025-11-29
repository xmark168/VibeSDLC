"""add requirements column to stories

Revision ID: add_requirements_001
Revises: 56ca8647f446
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_requirements_001'
down_revision = '56ca8647f446'
branch_labels = None
depends_on = None


def upgrade():
    # Add requirements column to stories table (JSON type for storing list of requirements)
    op.add_column('stories', sa.Column('requirements', postgresql.JSON(), nullable=True))


def downgrade():
    # Remove requirements column from stories table
    op.drop_column('stories', 'requirements')
