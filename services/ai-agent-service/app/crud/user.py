from typing import Any
from uuid import UUID

from sqlmodel import Session, select
from fastapi import HTTPException, status

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
    """
    Authenticate user by email or username and password
    Implements account locking after failed login attempts
    """
    db_user = get_user_by_email_or_username(session=session, email_or_username=email_or_username)
    if not db_user:
        return None

    # Check if account is locked
    if db_user.is_locked and db_user.locked_until:
        if db_user.locked_until > datetime.now(timezone.utc):
            remaining_minutes = int((db_user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account temporarily locked. Try again in {remaining_minutes} minutes."
            )
        else:
            # Unlock account if lock period has expired
            db_user.is_locked = False
            db_user.locked_until = None
            db_user.failed_login_attempts = 0
            session.add(db_user)
            session.commit()

    # Verify password
    if not verify_password(password, db_user.hashed_password):
        # Increment failed attempts
        db_user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if db_user.failed_login_attempts >= 5:
            db_user.is_locked = True
            db_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            session.add(db_user)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Account locked for 15 minutes."
            )

        session.add(db_user)
        session.commit()
        return None

    # Check if account is active
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact support."
        )

    # Reset failed attempts on successful login
    if db_user.failed_login_attempts > 0:
        db_user.failed_login_attempts = 0
        session.add(db_user)
        session.commit()

    return db_user


# Refresh Token CRUD
def create_refresh_token(
    *,
    session: Session,
    user_id: UUID,
    family_id: UUID | None = None,
    parent_token_id: UUID | None = None
) -> RefreshToken:
    """
    Create a new refresh token for user
    Supports token family tracking for rotation detection
    """
    from uuid import uuid4

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
        is_revoked=False,
        family_id=family_id or uuid4(),  # Create new family if not provided
        parent_token_id=parent_token_id
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


def revoke_all_tokens_in_family(*, session: Session, family_id: UUID) -> None:
    """Revoke all refresh tokens in a token family (for rotation detection)"""
    statement = select(RefreshToken).where(
        RefreshToken.family_id == family_id,
        RefreshToken.is_revoked == False
    )
    tokens = session.exec(statement).all()
    for token in tokens:
        token.is_revoked = True
        session.add(token)
    session.commit()


def validate_refresh_token(*, session: Session, token: str) -> RefreshToken | None:
    """
    Validate refresh token with rotation detection
    If a revoked token is reused, revoke entire token family (possible token theft)
    """
    db_token = get_refresh_token(session=session, token=token)
    if not db_token:
        return None

    # SECURITY: If revoked token is reused, revoke entire family
    if db_token.is_revoked:
        # Possible token theft - revoke all tokens in family
        revoke_all_tokens_in_family(session=session, family_id=db_token.family_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected. All sessions have been terminated for security.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if db_token.expires_at < datetime.now(timezone.utc):
        return None

    return db_token
