"""add_running_port_pid_to_story

Revision ID: 29accaff9533
Revises: 062c6f1a8706
Create Date: 2025-12-10 16:48:00.906786

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '29accaff9533'
down_revision = '062c6f1a8706'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('stories', sa.Column('running_port', sa.Integer(), nullable=True))
    op.add_column('stories', sa.Column('running_pid', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('stories', 'running_pid')
    op.drop_column('stories', 'running_port')
