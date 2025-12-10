"""add story_logs table

Revision ID: 0b756c60b09b
Revises: 0ed89de50ce6
Create Date: 2025-12-11 05:25:59.717966

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = '0b756c60b09b'
down_revision = '0ed89de50ce6'
branch_labels = None
depends_on = None


def upgrade():
    # Create story_logs table only
    op.create_table('story_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('story_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('level', sa.Enum('debug', 'info', 'warning', 'error', 'success', name='loglevel'), nullable=False),
        sa.Column('node', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_story_logs_story_id'), 'story_logs', ['story_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_story_logs_story_id'), table_name='story_logs')
    op.drop_table('story_logs')
    op.execute('DROP TYPE IF EXISTS loglevel')
