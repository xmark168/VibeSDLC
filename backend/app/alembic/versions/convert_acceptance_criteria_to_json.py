"""convert acceptance_criteria from Text to JSON array

Revision ID: convert_ac_to_json_001
Revises: add_requirements_001
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'convert_ac_to_json_001'
down_revision = 'add_requirements_001'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add new JSON column
    op.add_column('stories', sa.Column('acceptance_criteria_new', postgresql.JSON(), nullable=True))
    
    # Step 2: Migrate data from Text to JSON array
    # Convert "- AC1\n- AC2\n- AC3" to ["AC1", "AC2", "AC3"]
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE stories 
        SET acceptance_criteria_new = (
            SELECT jsonb_agg(trim(both '- ' from item))
            FROM unnest(string_to_array(acceptance_criteria, E'\n')) AS item
            WHERE trim(item) != ''
        )
        WHERE acceptance_criteria IS NOT NULL AND acceptance_criteria != ''
    """))
    
    # Step 3: Drop old column and rename new column
    op.drop_column('stories', 'acceptance_criteria')
    op.alter_column('stories', 'acceptance_criteria_new', new_column_name='acceptance_criteria')


def downgrade():
    # Step 1: Add back Text column
    op.add_column('stories', sa.Column('acceptance_criteria_old', sa.Text(), nullable=True))
    
    # Step 2: Convert JSON array back to Text format
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE stories 
        SET acceptance_criteria_old = (
            SELECT string_agg('- ' || item, E'\n')
            FROM jsonb_array_elements_text(acceptance_criteria) AS item
        )
        WHERE acceptance_criteria IS NOT NULL
    """))
    
    # Step 3: Drop JSON column and rename old column
    op.drop_column('stories', 'acceptance_criteria')
    op.alter_column('stories', 'acceptance_criteria_old', new_column_name='acceptance_criteria')
