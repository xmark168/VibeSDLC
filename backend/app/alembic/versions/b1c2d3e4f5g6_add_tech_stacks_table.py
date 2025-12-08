"""add tech_stacks table

Revision ID: b1c2d3e4f5g6
Revises: 3d738663d548
Create Date: 2025-12-08 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = '3d738663d548'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tech_stacks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('image', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('stack_config', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_tech_stacks_code'), 'tech_stacks', ['code'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_tech_stacks_code'), table_name='tech_stacks')
    op.drop_table('tech_stacks')
