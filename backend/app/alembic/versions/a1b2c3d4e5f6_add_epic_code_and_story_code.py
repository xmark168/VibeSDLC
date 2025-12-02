"""add epic_code and story_code

Revision ID: a1b2c3d4e5f6
Revises: 5b87d30158a9
Create Date: 2025-12-02 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '5b87d30158a9'
branch_labels = None
depends_on = None


def upgrade():
    # Add epic_code to epics table
    op.add_column('epics', sa.Column('epic_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))
    
    # Add story_code to stories table
    op.add_column('stories', sa.Column('story_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))


def downgrade():
    op.drop_column('stories', 'story_code')
    op.drop_column('epics', 'epic_code')
