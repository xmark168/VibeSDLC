"""remove_ba_workflow_tables

Revision ID: 76c81989b256
Revises: dad99eb90725
Create Date: 2025-11-23 20:22:17.911888

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '76c81989b256'
down_revision = 'dad99eb90725'
branch_labels = None
depends_on = None


def upgrade():
    """Drop BA workflow tables (child tables first, then parent)."""
    # Drop child tables first (they have foreign keys to ba_sessions)
    # Use IF EXISTS to avoid errors if tables were already dropped or never created
    op.execute('DROP TABLE IF EXISTS business_flows CASCADE')
    op.execute('DROP TABLE IF EXISTS product_briefs CASCADE')
    op.execute('DROP TABLE IF EXISTS requirements CASCADE')
    
    # Drop parent table last
    op.execute('DROP TABLE IF EXISTS ba_sessions CASCADE')


def downgrade():
    """Downgrade not implemented - BA workflow tables are being permanently removed."""
    pass
