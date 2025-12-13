"""add db_container_id and db_port to projects

Revision ID: add_db_container_proj
Revises: add_tech_stacks_table
Create Date: 2025-12-13

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_db_container_proj'
down_revision = 'add_tech_stacks_table'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projects', sa.Column('db_container_id', sa.String(length=100), nullable=True))
    op.add_column('projects', sa.Column('db_port', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('projects', 'db_port')
    op.drop_column('projects', 'db_container_id')
