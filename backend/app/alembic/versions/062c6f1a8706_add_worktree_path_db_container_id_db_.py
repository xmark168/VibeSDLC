"""Add worktree_path, db_container_id, db_port to stories

Revision ID: 062c6f1a8706
Revises: 50bde58e62a4
Create Date: 2025-12-10 15:00:45.788329

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '062c6f1a8706'
down_revision = '50bde58e62a4'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to stories table for worktree and db container tracking
    op.add_column('stories', sa.Column('worktree_path', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))
    op.add_column('stories', sa.Column('db_container_id', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))
    op.add_column('stories', sa.Column('db_port', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('stories', 'db_port')
    op.drop_column('stories', 'db_container_id')
    op.drop_column('stories', 'worktree_path')
