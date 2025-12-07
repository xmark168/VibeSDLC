"""Linked Account schemas for OAuth account linking."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.models import OAuthProvider


class LinkedAccountBase(BaseModel):
    provider: OAuthProvider
    provider_email: str


class LinkedAccountPublic(LinkedAccountBase):
    """Public representation of a linked account"""
    id: UUID
    provider_user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class LinkedAccountsResponse(BaseModel):
    """Response containing all linked accounts for a user"""
    linked_accounts: list[LinkedAccountPublic]
    available_providers: list[str]  # Providers not yet linked


class LinkAccountRequest(BaseModel):
    """Request to initiate account linking"""
    provider: OAuthProvider


class UnlinkAccountRequest(BaseModel):
    """Request to unlink an account"""
    provider: OAuthProvider
    password: str | None = Field(
        default=None,
        description="Required if this is the last login method and user has no password"
    )


class UnlinkAccountResponse(BaseModel):
    """Response after unlinking an account"""
    message: str
    remaining_providers: list[str]


class LinkCallbackResponse(BaseModel):
    """Response after successfully linking an account"""
    message: str
    provider: str
    provider_email: str
