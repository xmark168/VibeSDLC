"""Remove Sprint model and migrate to Kanban

Revision ID: 95bxhq8r0tb1
Revises: c204442532e1
Create Date: 2025-11-16 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '95bxhq8r0tb1'
down_revision = 'c204442532e1'
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate from Sprint-based Scrum to Kanban:
    1. Add project_id to backlog_items
    2. Populate project_id from sprints
    3. Remove sprint_id from backlog_items
    4. Remove sprint fields from issue_activities
    5. Drop sprints table
    """

    # Step 1: Add project_id column to backlog_items (nullable initially)
    op.add_column('backlog_items', sa.Column('project_id', sa.Uuid(), nullable=True))

    # Step 2: Populate project_id from sprints.project_id
    op.execute("""
        UPDATE backlog_items
        SET project_id = sprints.project_id
        FROM sprints
        WHERE backlog_items.sprint_id = sprints.id
    """)

    # Step 3: Make project_id NOT NULL
    op.alter_column('backlog_items', 'project_id', nullable=False)

    # Step 4: Add index on project_id for performance
    op.create_index(op.f('ix_backlog_items_project_id'), 'backlog_items', ['project_id'], unique=False)

    # Step 5: Add foreign key constraint for project_id
    op.create_foreign_key('fk_backlog_items_project_id', 'backlog_items', 'projects', ['project_id'], ['id'], ondelete='CASCADE')

    # Step 6: Drop foreign key constraint for sprint_id
    op.drop_constraint('backlog_items_sprint_id_fkey', 'backlog_items', type_='foreignkey')

    # Step 7: Drop sprint_id column
    op.drop_column('backlog_items', 'sprint_id')

    # Step 8: Drop sprint_from and sprint_to columns from issue_activities
    op.drop_column('issue_activities', 'sprint_from')
    op.drop_column('issue_activities', 'sprint_to')

    # Step 9: Drop sprints table
    op.drop_table('sprints')


def downgrade():
    """
    Rollback: Restore Sprint-based Scrum structure
    WARNING: This will result in data loss as Sprint data has been deleted
    """

    # Step 1: Recreate sprints table
    op.create_table('sprints',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('goal', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('velocity_plan', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('velocity_actual', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Step 2: Add sprint_from and sprint_to back to issue_activities
    op.add_column('issue_activities', sa.Column('sprint_from', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('issue_activities', sa.Column('sprint_to', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # Step 3: Add sprint_id column back to backlog_items (nullable, since we can't restore Sprint data)
    op.add_column('backlog_items', sa.Column('sprint_id', sa.Uuid(), nullable=True))

    # Step 4: Create foreign key constraint for sprint_id (but it will point to empty sprints table)
    op.create_foreign_key('backlog_items_sprint_id_fkey', 'backlog_items', 'sprints', ['sprint_id'], ['id'], ondelete='CASCADE')

    # Step 5: Drop project_id foreign key
    op.drop_constraint('fk_backlog_items_project_id', 'backlog_items', type_='foreignkey')

    # Step 6: Drop project_id index
    op.drop_index(op.f('ix_backlog_items_project_id'), table_name='backlog_items')

    # Step 7: Drop project_id column
    op.drop_column('backlog_items', 'project_id')

    # Note: After downgrade, backlog_items will have sprint_id = NULL
    # Manual intervention required to create Sprints and reassign backlog items
