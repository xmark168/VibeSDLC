"""add_pr_url_merge_status_to_story

Revision ID: 44a7adba6797
Revises: 29accaff9533
Create Date: 2025-12-10 18:14:35.247200

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '44a7adba6797'
down_revision = '29accaff9533'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('stories', sa.Column('pr_url', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))
    op.add_column('stories', sa.Column('merge_status', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))


def downgrade():
    op.drop_column('stories', 'merge_status')
    op.drop_column('stories', 'pr_url')
