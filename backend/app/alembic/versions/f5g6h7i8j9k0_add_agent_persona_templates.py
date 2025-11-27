"""Add agent persona templates

Revision ID: f5g6h7i8j9k0
Revises: e4a1b2c3d4e5
Create Date: 2025-11-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f5g6h7i8j9k0'
down_revision: Union[str, None] = 'e4a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_persona_templates table
    op.create_table(
        'agent_persona_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('role_type', sa.String(), nullable=False),
        sa.Column('personality_traits', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('communication_style', sa.String(), nullable=False),
        sa.Column('work_approach', sa.String(), nullable=False),
        sa.Column('backstory', sa.Text(), nullable=True),
        sa.Column('quirks', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('persona_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'role_type', name='uq_persona_name_role')
    )
    op.create_index(op.f('ix_agent_persona_templates_name'), 'agent_persona_templates', ['name'], unique=False)
    op.create_index(op.f('ix_agent_persona_templates_role_type'), 'agent_persona_templates', ['role_type'], unique=False)
    
    # Add persona_template_id to agents table
    op.add_column('agents', sa.Column('persona_template_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add persona fields to agents table (denormalized)
    op.add_column('agents', sa.Column('personality_traits', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('agents', sa.Column('communication_style', sa.String(), nullable=True))
    op.add_column('agents', sa.Column('work_approach', sa.String(), nullable=True))
    op.add_column('agents', sa.Column('backstory', sa.Text(), nullable=True))
    op.add_column('agents', sa.Column('quirks', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('agents', sa.Column('persona_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_agent_persona_template',
        'agents', 'agent_persona_templates',
        ['persona_template_id'], ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_agent_persona_template', 'agents', type_='foreignkey')
    
    # Drop persona fields from agents table
    op.drop_column('agents', 'persona_metadata')
    op.drop_column('agents', 'quirks')
    op.drop_column('agents', 'backstory')
    op.drop_column('agents', 'work_approach')
    op.drop_column('agents', 'communication_style')
    op.drop_column('agents', 'personality_traits')
    op.drop_column('agents', 'persona_template_id')
    
    # Drop indexes
    op.drop_index(op.f('ix_agent_persona_templates_role_type'), table_name='agent_persona_templates')
    op.drop_index(op.f('ix_agent_persona_templates_name'), table_name='agent_persona_templates')
    
    # Drop agent_persona_templates table
    op.drop_table('agent_persona_templates')
