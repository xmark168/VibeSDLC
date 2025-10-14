from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"

# class BaseModel(SQLModel):
    # id: User

# Shared properties
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    role: Role = Field(default=Role.USER, nullable=True)
    create_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    refresh_tokens: list["RefreshToken"] = Relationship(back_populates="user")

class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=False)
    token: str = Field(unique=True, index=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_revoked: bool = Field(default=False)

    # Relationship
    user: User | None = Relationship(back_populates="refresh_tokens")

