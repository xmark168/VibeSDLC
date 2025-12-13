from sqlmodel import Session, create_engine, select
from app.core.config import settings
from app.models import User, Role
from app.schemas import UserCreate
from app.services import UserService

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def get_worker_engine(pool_size: int = 5, max_overflow: int = 10):
    return create_engine(
        str(settings.SQLALCHEMY_DATABASE_URI),
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


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
