"""add_unique_constraint_to_story_code

Revision ID: a750959a13b0
Revises: 44a7adba6797
Create Date: 2025-12-10 18:30:02.861276

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a750959a13b0'
down_revision = '44a7adba6797'
branch_labels = None
depends_on = None


def upgrade():
    # First, fix any duplicate story_codes by appending ID suffix
    conn = op.get_bind()
    
    # Find duplicates
    result = conn.execute(sa.text("""
        SELECT story_code, array_agg(id ORDER BY created_at) as ids
        FROM stories 
        WHERE story_code IS NOT NULL
        GROUP BY story_code 
        HAVING COUNT(*) > 1
    """))
    
    for row in result:
        story_code = row[0]
        ids = row[1]
        # Keep first one, update others with suffix
        for i, story_id in enumerate(ids[1:], start=2):
            new_code = f"{story_code}-{i}"
            conn.execute(
                sa.text("UPDATE stories SET story_code = :new_code WHERE id = :id"),
                {"new_code": new_code, "id": story_id}
            )
    
    # Now create the unique index
    op.create_index(op.f('ix_stories_story_code'), 'stories', ['story_code'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_stories_story_code'), table_name='stories')
