from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import User
from app.schemas import UserCreate, UserUpdate
from datetime import datetime, timezone, timedelta
from app.models import RefreshToken
from app.core.config import settings
import secrets


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def get_user_by_username(*, session: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    session_user = session.exec(statement).first()
    return session_user


def get_user_by_email_or_username(*, session: Session, email_or_username: str) -> User | None:
    """Get user by email or username"""
    statement = select(User).where(
        (User.email == email_or_username) | (User.username == email_or_username)
    )
    return session.exec(statement).first()


def authenticate(*, session: Session, email_or_username: str, password: str) -> User | None:
    """Authenticate user by email or username and password"""
    db_user = get_user_by_email_or_username(session=session, email_or_username=email_or_username)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


# Refresh Token CRUD
def create_refresh_token(*, session: Session, user_id: UUID) -> RefreshToken:
    """Create a new refresh token for user"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
        is_revoked=False
    )
    session.add(db_token)
    session.commit()
    session.refresh(db_token)
    return db_token


def get_refresh_token(*, session: Session, token: str) -> RefreshToken | None:
    """Get refresh token by token string"""
    statement = select(RefreshToken).where(RefreshToken.token == token)
    return session.exec(statement).first()


def revoke_refresh_token(*, session: Session, token: str) -> bool:
    """Revoke a refresh token"""
    db_token = get_refresh_token(session=session, token=token)
    if not db_token:
        return False
    db_token.is_revoked = True
    session.add(db_token)
    session.commit()
    return True


def revoke_all_user_tokens(*, session: Session, user_id: UUID) -> None:
    """Revoke all refresh tokens for a user"""
    statement = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    )
    tokens = session.exec(statement).all()
    for token in tokens:
        token.is_revoked = True
        session.add(token)
    session.commit()


def validate_refresh_token(*, session: Session, token: str) -> RefreshToken | None:
    """Validate refresh token (check if exists, not revoked, not expired)"""
    db_token = get_refresh_token(session=session, token=token)
    if not db_token:
        return None
    if db_token.is_revoked:
        return None
    if db_token.expires_at < datetime.now(timezone.utc):
        return None
    return db_token
