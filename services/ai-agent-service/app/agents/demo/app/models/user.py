"""
User model for authentication and user management.
"""

from app.core.database import Base
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    """User model for authentication and profile management."""

    __tablename__ = "users"

    # Basic info
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Authentication
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Profile
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Verification
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_password_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"

is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)