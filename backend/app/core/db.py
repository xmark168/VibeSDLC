from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, Role
from app.schemas import UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

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
