"""add_checkpoint_thread_id_to_story

Revision ID: da61b7fe3860
Revises: a750959a13b0
Create Date: 2025-12-10 20:10:36.383631

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'da61b7fe3860'
down_revision = 'a750959a13b0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('stories', sa.Column('checkpoint_thread_id', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))


def downgrade():
    op.drop_column('stories', 'checkpoint_thread_id')
