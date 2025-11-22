"""Update agent model with project_id and new fields

Revision ID: 7f410bab7ebe
Revises: 069a4531ca82
Create Date: 2025-11-22 11:11:55.495983

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '7f410bab7ebe'
down_revision = '069a4531ca82'
branch_labels = None
depends_on = None


def upgrade():
    # Create the enum type first
    op.execute("CREATE TYPE agentstatus AS ENUM ('idle', 'busy', 'stopped', 'error')")

    # Add columns as nullable first
    op.add_column('agents', sa.Column('project_id', sa.Uuid(), nullable=True))
    op.add_column('agents', sa.Column('human_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('agents', sa.Column('role_type', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('agents', sa.Column('status', sa.Enum('idle', 'busy', 'stopped', 'error', name='agentstatus', create_type=False), nullable=True))

    # Delete any existing agents without project_id (they're orphaned)
    op.execute("DELETE FROM agents WHERE project_id IS NULL")

    # Now make columns NOT NULL
    op.alter_column('agents', 'project_id', nullable=False)
    op.alter_column('agents', 'human_name', nullable=False, server_default='Agent')
    op.alter_column('agents', 'role_type', nullable=False, server_default='developer')
    op.alter_column('agents', 'status', nullable=False, server_default='idle')

    # Remove server defaults
    op.alter_column('agents', 'human_name', server_default=None)
    op.alter_column('agents', 'role_type', server_default=None)
    op.alter_column('agents', 'status', server_default=None)

    # Add index and foreign key
    op.create_index(op.f('ix_agents_project_id'), 'agents', ['project_id'], unique=False)
    op.create_foreign_key('fk_agents_project_id', 'agents', 'projects', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('fk_agents_project_id', 'agents', type_='foreignkey')
    op.drop_index(op.f('ix_agents_project_id'), table_name='agents')
    op.drop_column('agents', 'status')
    op.drop_column('agents', 'role_type')
    op.drop_column('agents', 'human_name')
    op.drop_column('agents', 'project_id')
    op.execute("DROP TYPE agentstatus")
