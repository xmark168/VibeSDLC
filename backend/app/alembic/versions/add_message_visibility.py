"""add message visibility field

Revision ID: add_message_visibility
Revises: 9cf465c64651
Create Date: 2025-11-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'add_message_visibility'
down_revision = '9cf465c64651'
branch_labels = None
depends_on = None


def upgrade():
    """Add visibility column to messages table"""
    # Create enum type for message visibility
    op.execute("CREATE TYPE messagevisibility AS ENUM ('user_message', 'system_log')")
    
    # Add visibility column with default 'user_message'
    op.add_column('messages', 
        sa.Column('visibility', 
                  sa.Enum('user_message', 'system_log', name='messagevisibility'),
                  nullable=False,
                  server_default='user_message'
        )
    )


def downgrade():
    """Remove visibility column from messages table"""
    op.drop_column('messages', 'visibility')
    op.execute("DROP TYPE messagevisibility")
