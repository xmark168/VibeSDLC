"""Fix AgentStatus enum values

Revision ID: 202511220001
Revises: f05a3d39d58d
Create Date: 2025-11-22 18:56:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '202511220001'
down_revision = 'f8d99ad955cb'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing enum values to AgentStatus if they don't exist
    op.execute("""
        DO $$
        BEGIN
            -- Add 'starting' if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'starting' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'agentstatus')) THEN
                ALTER TYPE agentstatus ADD VALUE 'starting';
            END IF;

            -- Add 'stopping' if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'stopping' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'agentstatus')) THEN
                ALTER TYPE agentstatus ADD VALUE 'stopping';
            END IF;

            -- Add 'stopped' if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'stopped' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'agentstatus')) THEN
                ALTER TYPE agentstatus ADD VALUE 'stopped';
            END IF;

            -- Add 'busy' if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'busy' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'agentstatus')) THEN
                ALTER TYPE agentstatus ADD VALUE 'busy';
            END IF;

            -- Add 'terminated' if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'terminated' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'agentstatus')) THEN
                ALTER TYPE agentstatus ADD VALUE 'terminated';
            END IF;
        END
        $$;
    """)


def downgrade():
    # Cannot easily remove enum values in PostgreSQL, so we'll leave them
    pass
