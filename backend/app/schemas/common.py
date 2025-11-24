"""Common/shared schemas."""

from sqlmodel import SQLModel


class Message(SQLModel):
    """Generic message response."""
    message: str


class NewPassword(SQLModel):
    """Password reset schema."""
    token: str
    new_password: str
