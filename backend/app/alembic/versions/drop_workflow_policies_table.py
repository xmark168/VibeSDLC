"""drop workflow_policies table

Revision ID: drop_workflow_policies
Revises: 44b968bd22f7
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'drop_workflow_policies'
down_revision = '44b968bd22f7'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('workflow_policies')


def downgrade():
    op.create_table(
        'workflow_policies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=False),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('criteria', sa.JSON(), nullable=True),
        sa.Column('required_role', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_workflow_policies_project_id', 'workflow_policies', ['project_id'])
