import os
from sqlmodel import Session, create_engine, select
from pydantic import PostgresDsn

from app import crud
from app.core.config import settings
from app.models import User, Role
from app.schemas import UserCreate

# Main engine for FastAPI master process
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def get_worker_engine(pool_size: int = 5, max_overflow: int = 10):
    """Get database engine for worker processes.

    This creates a fresh engine instance for worker processes to avoid
    connection pool corruption when using multiprocessing.

    If PGBOUNCER_URL is set in environment, uses that instead of direct
    PostgreSQL connection for better connection pooling.

    Args:
        pool_size: Connection pool size for this worker
        max_overflow: Max overflow connections

    Returns:
        SQLModel engine instance
    """
    # Check for PgBouncer URL in environment
    pgbouncer_url = os.getenv("PGBOUNCER_URL")

    if pgbouncer_url:
        # Use PgBouncer (connection pooler)
        # PgBouncer URL format: postgresql+psycopg://user:pass@pgbouncer_host:6432/dbname
        db_url = pgbouncer_url
    else:
        # Fallback to direct PostgreSQL connection
        db_url = str(settings.SQLALCHEMY_DATABASE_URI)

    # Create engine with worker-specific pool settings
    worker_engine = create_engine(
        db_url,
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
        user = crud.create_user(session=session, user_create=user_in)
        user.role = Role.ADMIN
        session.add(user)
        session.commit()
        session.refresh(user)
