from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.core.security import get_password_hash
from app.models import User
from app.schemas import UserPublic, GitHubInstallationPublic

router = APIRouter(tags=["private"], prefix="/private")


class PrivateUserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    is_verified: bool = False


def user_to_public_private(user: User) -> UserPublic:
    """
    Convert User model to UserPublic schema with GitHub installation data.
    Similar to users.py but for private API.
    """
    github_installation_id = None
    github_installations_public = None

    if user.github_installations and len(user.github_installations) > 0:
        github_installation_id = user.github_installations[0].installation_id

        github_installations_public = [
            GitHubInstallationPublic(
                id=installation.id,
                installation_id=installation.installation_id,
                account_login=installation.account_login,
                account_type=installation.account_type,
                account_status=installation.account_status,
                repositories=installation.repositories,
                user_id=installation.user_id,
                created_at=installation.created_at,
                updated_at=installation.updated_at,
            )
            for installation in user.github_installations
        ]

    return UserPublic(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        github_installation_id=github_installation_id,
        github_installations=github_installations_public,
    )


@router.post("/users/", response_model=UserPublic)
def create_user(user_in: PrivateUserCreate, session: SessionDep) -> Any:
    """
    Create a new user.
    """

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
    )

    session.add(user)
    session.commit()

    # Refresh to load github_installations relationship
    session.refresh(user, attribute_names=["github_installations"])

    return user_to_public_private(user)
