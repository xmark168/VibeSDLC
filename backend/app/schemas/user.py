"""User-related schemas."""

from uuid import UUID
from typing import Optional
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from app.models import Role


class UserPublic(SQLModel):
    id: UUID
    full_name: Optional[str] = None
    email: EmailStr
    role: Role


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class UserCreate(SQLModel):
    username: str | None = None
    password: str
    email: EmailStr


class UserLogin(SQLModel):
    email_or_username: str
    password: str


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserUpdateMe(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)


class UserRegister(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=3)
