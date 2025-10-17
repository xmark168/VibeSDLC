from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from .models import Role

class UserPublic(SQLModel):
    id: UUID
    username: str
    email: EmailStr
    role: Role

class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int

class UserCreate(SQLModel): 
    username: str
    password: str
    email: EmailStr

class UserLogin(SQLModel):
    email_or_username: str 
    password: str

