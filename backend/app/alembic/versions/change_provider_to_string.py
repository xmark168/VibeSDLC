"""Change provider column from enum to string

Revision ID: change_provider_string
Revises: add_linked_accounts
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'change_provider_string'
down_revision = 'add_linked_accounts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change provider column from enum to varchar
    op.execute("""
        ALTER TABLE linked_accounts 
        ALTER COLUMN provider TYPE VARCHAR(20) 
        USING provider::text
    """)
    
    # Drop the enum type (optional, but keeps DB clean)
    op.execute("DROP TYPE IF EXISTS oauthprovider")


def downgrade() -> None:
    # Recreate enum type
    op.execute("CREATE TYPE oauthprovider AS ENUM ('google', 'github', 'facebook')")
    
    # Change back to enum
    op.execute("""
        ALTER TABLE linked_accounts 
        ALTER COLUMN provider TYPE oauthprovider 
        USING provider::oauthprovider
    """)
