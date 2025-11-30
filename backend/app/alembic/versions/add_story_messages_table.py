"""Add story_messages table and drop comments table

Revision ID: add_story_messages
Revises: 056c59419f8c
Create Date: 2024-11-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_story_messages'
down_revision: Union[str, None] = 'add_requirements_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create story_messages table
    op.create_table('story_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('story_id', sa.Uuid(), nullable=False),
        sa.Column('author_type', sa.String(), nullable=False),
        sa.Column('author_name', sa.String(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=True),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(), nullable=False, server_default='update'),
        sa.Column('structured_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_story_messages_story_id'), 'story_messages', ['story_id'], unique=False)
    
    # Drop unused comments table
    op.drop_table('comments')


def downgrade() -> None:
    # Recreate comments table
    op.create_table('comments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('backlog_item_id', sa.Uuid(), nullable=False),
        sa.Column('commenter_id', sa.Uuid(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['backlog_item_id'], ['stories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['commenter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Drop story_messages table
    op.drop_index(op.f('ix_story_messages_story_id'), table_name='story_messages')
    op.drop_table('story_messages')
