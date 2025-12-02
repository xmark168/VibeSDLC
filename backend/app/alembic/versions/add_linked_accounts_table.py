"""Add linked_accounts table for OAuth linking

Revision ID: add_linked_accounts
Revises: add_2fa_fields
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = 'add_linked_accounts'
down_revision = 'add_2fa_fields'
branch_labels = None
depends_on = None

# Define enum without auto-create
oauthprovider_enum = ENUM('google', 'github', 'facebook', name='oauthprovider', create_type=False)


def upgrade() -> None:
    # Create oauthprovider enum (if not exists)
    op.execute("DO $$ BEGIN CREATE TYPE oauthprovider AS ENUM ('google', 'github', 'facebook'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    
    # Create linked_accounts table
    op.create_table(
        'linked_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', oauthprovider_enum, nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('provider_email', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )
    op.create_index('ix_linked_accounts_user_id', 'linked_accounts', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_linked_accounts_user_id', table_name='linked_accounts')
    op.drop_table('linked_accounts')
    op.execute("DROP TYPE IF EXISTS oauthprovider")
