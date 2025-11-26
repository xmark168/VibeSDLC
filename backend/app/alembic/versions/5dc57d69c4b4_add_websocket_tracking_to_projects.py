"""add websocket tracking to projects

Revision ID: 5dc57d69c4b4
Revises: c7c993f630ef
Create Date: 2025-11-25 16:13:43.927254

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '5dc57d69c4b4'
down_revision = 'c7c993f630ef'
branch_labels = None
depends_on = None


def upgrade():
    # Add WebSocket tracking fields to projects table
    op.add_column('projects',
        sa.Column('websocket_connected', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('projects',
        sa.Column('websocket_last_seen', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    # Remove WebSocket tracking fields
    op.drop_column('projects', 'websocket_last_seen')
    op.drop_column('projects', 'websocket_connected')
