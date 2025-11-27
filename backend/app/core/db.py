import os
from sqlmodel import Session, create_engine, select
from pydantic import PostgresDsn

from app.core.config import settings
from app.models import User, Role
from app.schemas import UserCreate
from app.services import UserService

# Main engine for FastAPI master process
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def get_worker_engine(pool_size: int = 5, max_overflow: int = 10):
    """Get database engine for background tasks and workers.

    Creates a fresh engine instance with custom pool settings for
    background tasks like metrics collection.

    Args:
        pool_size: Connection pool size
        max_overflow: Max overflow connections

    Returns:
        SQLModel engine instance
    """
    worker_engine = create_engine(
        str(settings.SQLALCHEMY_DATABASE_URI),
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
    )

    return worker_engine

def init_db(session: Session) -> None:
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
        )
        user_service = UserService(session)
        user = user_service.create(user_in)
        user.role = Role.ADMIN
        session.add(user)
        session.commit()
        session.refresh(user)
