"""add_description_color_icon_to_projects

Revision ID: 3c12fd52b38e
Revises: 2a3720fc9b9a
Create Date: 2025-11-14 16:37:24.457075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c12fd52b38e'
down_revision: Union[str, Sequence[str], None] = '2a3720fc9b9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add description column to projects table
    op.add_column('projects', sa.Column('description', sa.Text(), nullable=True))

    # Add color column to projects table (hex color code, e.g., #FF5733)
    op.add_column('projects', sa.Column('color', sa.String(length=7), nullable=True))

    # Add icon column to projects table (icon name or emoji)
    op.add_column('projects', sa.Column('icon', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove icon column
    op.drop_column('projects', 'icon')

    # Remove color column
    op.drop_column('projects', 'color')

    # Remove description column
    op.drop_column('projects', 'description')
