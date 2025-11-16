"""CRUD operations for GitHub Installation model."""

from uuid import UUID
from sqlmodel import Session, select
from app.models import GitHubInstallation, User
from app.schemas import GitHubInstallationCreate, GitHubInstallationUpdate


def create_github_installation(
    session: Session, installation_create: GitHubInstallationCreate
) -> GitHubInstallation:
    """Create a new GitHub installation record."""
    db_installation = GitHubInstallation(
        installation_id=installation_create.installation_id,
        account_login=installation_create.account_login,
        account_type=installation_create.account_type,
        repositories=installation_create.repositories,
        user_id=installation_create.user_id,
    )
    session.add(db_installation)
    session.commit()
    session.refresh(db_installation)
    return db_installation


def get_github_installation(
    session: Session, installation_id: UUID
) -> GitHubInstallation | None:
    """Get a GitHub installation by ID."""
    statement = select(GitHubInstallation).where(
        GitHubInstallation.id == installation_id
    )
    return session.exec(statement).first()


def get_github_installation_by_installation_id(
    session: Session, installation_id: int
) -> GitHubInstallation | None:
    """Get a GitHub installation by GitHub installation ID."""
    statement = select(GitHubInstallation).where(
        GitHubInstallation.installation_id == installation_id
    )
    return session.exec(statement).first()


def get_github_installations_by_user(
    session: Session, user_id: UUID, skip: int = 0, limit: int = 10
) -> list[GitHubInstallation]:
    """Get all GitHub installations for a user."""
    statement = (
        select(GitHubInstallation)
        .where(GitHubInstallation.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return session.exec(statement).all()


def count_github_installations_by_user(
    session: Session, user_id: UUID
) -> int:
    """Count GitHub installations for a user."""
    statement = select(GitHubInstallation).where(
        GitHubInstallation.user_id == user_id
    )
    return len(session.exec(statement).all())


def update_github_installation(
    session: Session,
    installation_id: UUID,
    installation_update: GitHubInstallationUpdate,
) -> GitHubInstallation | None:
    """Update a GitHub installation."""
    db_installation = get_github_installation(session, installation_id)
    if not db_installation:
        return None

    update_data = installation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_installation, key, value)

    session.add(db_installation)
    session.commit()
    session.refresh(db_installation)
    return db_installation


def delete_github_installation(
    session: Session, installation_id: UUID
) -> bool:
    """Delete a GitHub installation."""
    db_installation = get_github_installation(session, installation_id)
    if not db_installation:
        return False

    session.delete(db_installation)
    session.commit()
    return True


def delete_github_installation_by_installation_id(
    session: Session, installation_id: int
) -> bool:
    """Delete a GitHub installation by GitHub installation ID."""
    db_installation = get_github_installation_by_installation_id(
        session, installation_id
    )
    if not db_installation:
        return False

    session.delete(db_installation)
    session.commit()
    return True

