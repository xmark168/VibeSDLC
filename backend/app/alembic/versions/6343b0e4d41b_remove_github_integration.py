"""remove_github_integration

Revision ID: 6343b0e4d41b
Revises: 0b0f13415291
Create Date: 2025-11-16 22:20:58.637129

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '6343b0e4d41b'
down_revision = '0b0f13415291'
branch_labels = None
depends_on = None


def upgrade():
    # Drop GitHub-related columns from projects table
    op.drop_constraint('projects_github_repository_url_key', 'projects', type_='unique')
    op.drop_column('projects', 'github_repository_name')
    op.drop_column('projects', 'github_repository_url')

    # Drop github_installations table
    op.drop_table('github_installations')

    # Drop GitHub-related enums
    sa.Enum(name='githubaccounttype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='githubinstallationstatus').drop(op.get_bind(), checkfirst=True)


def downgrade():
    # Recreate GitHub enums
    sa.Enum('USER', 'ORGANIZATION', name='githubaccounttype').create(op.get_bind())
    sa.Enum('PENDING', 'INSTALLED', 'DELETED', name='githubinstallationstatus').create(op.get_bind())

    # Recreate github_installations table
    op.create_table(
        'github_installations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('installation_id', sa.Integer(), nullable=False),
        sa.Column('account_login', sa.String(), nullable=False),
        sa.Column('account_type', sa.Enum('USER', 'ORGANIZATION', name='githubaccounttype'), nullable=False),
        sa.Column('account_status', sa.Enum('PENDING', 'INSTALLED', 'DELETED', name='githubinstallationstatus'), nullable=False),
        sa.Column('repositories', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_github_installations_account_status', 'github_installations', ['account_status'], unique=False)
    op.create_index('ix_github_installations_installation_id', 'github_installations', ['installation_id'], unique=True)

    # Recreate GitHub columns in projects table
    op.add_column('projects', sa.Column('github_repository_url', sa.String(), nullable=True))
    op.add_column('projects', sa.Column('github_repository_name', sa.String(), nullable=True))
    op.create_unique_constraint('projects_github_repository_url_key', 'projects', ['github_repository_url'])
