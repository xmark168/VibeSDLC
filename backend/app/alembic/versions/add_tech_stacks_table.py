"""add tech_stacks table

Revision ID: add_tech_stacks_table
Revises: add_pool_priority
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_tech_stacks_table'
down_revision = 'add_pool_priority'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('tech_stacks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('image', sa.String(length=500), nullable=True),
        sa.Column('stack_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tech_stacks_code'), 'tech_stacks', ['code'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_tech_stacks_code'), table_name='tech_stacks')
    op.drop_table('tech_stacks')
