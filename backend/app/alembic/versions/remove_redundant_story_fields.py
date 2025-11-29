"""Remove redundant story fields: estimate_value, story_priority, pause

Revision ID: remove_redundant_fields
Revises: 056c59419f8c
Create Date: 2024-11-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_redundant_fields'
down_revision = '056c59419f8c'
branch_labels = None
depends_on = None


def upgrade():
    # Drop redundant columns from stories table
    op.drop_column('stories', 'estimate_value')
    op.drop_column('stories', 'story_priority')
    op.drop_column('stories', 'pause')
    
    # Drop the storypriority enum type
    op.execute("DROP TYPE IF EXISTS storypriority")


def downgrade():
    # Recreate the storypriority enum type
    storypriority = sa.Enum('HIGH', 'MEDIUM', 'LOW', name='storypriority')
    storypriority.create(op.get_bind(), checkfirst=True)
    
    # Add back the columns
    op.add_column('stories', sa.Column('estimate_value', sa.Integer(), nullable=True))
    op.add_column('stories', sa.Column('story_priority', storypriority, nullable=True))
    op.add_column('stories', sa.Column('pause', sa.Boolean(), nullable=False, server_default='false'))
