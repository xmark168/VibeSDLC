"""add sepay fields to order

Revision ID: c3d4e5f6g7h8
Revises: b1c2d3e4f5g6
Create Date: 2025-12-08 15:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b1c2d3e4f5g6'
branch_labels = None
depends_on = None


def upgrade():
    # Add sepay_transaction_code column
    op.add_column('orders', sa.Column('sepay_transaction_code', sa.Text(), nullable=True))
    op.create_index(op.f('ix_orders_sepay_transaction_code'), 'orders', ['sepay_transaction_code'], unique=True)
    
    # Add sepay_transaction_id column
    op.add_column('orders', sa.Column('sepay_transaction_id', sa.Text(), nullable=True))


def downgrade():
    op.drop_index(op.f('ix_orders_sepay_transaction_code'), table_name='orders')
    op.drop_column('orders', 'sepay_transaction_id')
    op.drop_column('orders', 'sepay_transaction_code')
