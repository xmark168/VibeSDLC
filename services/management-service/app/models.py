from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"

class BaseModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory= lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False
    )

# Shared properties
class User(BaseModel, table=True):
    __tablename__ = "users"
    
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    role: Role = Field(default=Role.USER, nullable=True)

    # Relationship
    refresh_tokens: list["RefreshToken"] = Relationship(back_populates="user")

class RefreshToken(BaseModel, table=True):
    __tablename__ = "refresh_tokens"

    token: str = Field(unique=True, index=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    expires_at: datetime
    is_revoked: bool = Field(default=False)

    # Relationship
    user: User | None = Relationship(back_populates="refresh_tokens")

class Project(BaseModel, table=True):
    __tablename__ = "projects"

    code: str
    name: str
    owner_id: UUID = Field(foreign_key="users.id", nullable=False)

class Sprint(BaseModel, table=True):
    __tablename__ = "sprints"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    name: str
    number: number
    goal: str
    status: str
    start_date: datetime
    end_date: datetime
    velocity_plan: str
    
