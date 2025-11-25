"""remove_preview_data

Revision ID: e4a1b2c3d4e5
Revises: d3f8a9e12c45
Create Date: 2025-11-25 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4a1b2c3d4e5'
down_revision = 'd3f8a9e12c45'
branch_labels = None
depends_on = None


def upgrade():
    """Remove preview_data column from approval_requests table.
    
    This column is replaced by the new artifact system which provides
    structured, versioned documents instead of generic preview data.
    """
    op.drop_column('approval_requests', 'preview_data')


def downgrade():
    """Re-add preview_data column if needed."""
    op.add_column(
        'approval_requests',
        sa.Column('preview_data', sa.JSON(), nullable=True)
    )
