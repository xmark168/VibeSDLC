"""simplify_agent_persona_remove_deprecated_fields

Simplify agent persona template by removing work_approach, backstory, and quirks fields.
Keeps only personality_traits and communication_style for better CrewAI performance.

Revision ID: eae1d00a420d
Revises: f5g6h7i8j9k0
Create Date: 2025-11-26 14:36:03.971230

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'eae1d00a420d'
down_revision = 'f5g6h7i8j9k0'
branch_labels = None
depends_on = None


def upgrade():
    # Drop deprecated columns from agent_persona_templates table
    op.drop_column('agent_persona_templates', 'work_approach')
    op.drop_column('agent_persona_templates', 'backstory')
    op.drop_column('agent_persona_templates', 'quirks')
    
    # Drop deprecated columns from agents table (denormalized fields)
    op.drop_column('agents', 'work_approach')
    op.drop_column('agents', 'backstory')
    op.drop_column('agents', 'quirks')


def downgrade():
    # Re-add columns to agents table (denormalized fields)
    op.add_column('agents', sa.Column('quirks', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('agents', sa.Column('backstory', sa.Text(), nullable=True))
    op.add_column('agents', sa.Column('work_approach', sa.String(), nullable=True))
    
    # Re-add columns to agent_persona_templates table
    op.add_column('agent_persona_templates', sa.Column('quirks', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('agent_persona_templates', sa.Column('backstory', sa.Text(), nullable=False, server_default='Experienced agent'))
    op.add_column('agent_persona_templates', sa.Column('work_approach', sa.String(), nullable=False, server_default='systematic'))
