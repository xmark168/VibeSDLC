"""Linked Accounts API routes for OAuth account linking."""

import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.oauth import set_oauth_state  # Use shared OAuth state
from app.core.config import settings
from app.models import OAuthProvider
from app.schemas import (
    LinkedAccountPublic,
    LinkedAccountsResponse,
    UnlinkAccountRequest,
    UnlinkAccountResponse,
)
from app.services import LinkedAccountService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["linked-accounts"])

# OAuth configurations
GOOGLE_CLIENT_ID = getattr(settings, "GOOGLE_CLIENT_ID", "")
GITHUB_CLIENT_ID = getattr(settings, "GITHUB_CLIENT_ID", "")
FACEBOOK_APP_ID = getattr(settings, "FACEBOOK_APP_ID", "")


@router.get("/linked", response_model=LinkedAccountsResponse)
def get_linked_accounts(
    current_user: CurrentUser,
    session: SessionDep,
) -> LinkedAccountsResponse:
    """Get all linked OAuth accounts for current user."""
    service = LinkedAccountService(session)
    linked = service.get_linked_accounts(current_user.id)
    available = service.get_available_providers(current_user.id)

    return LinkedAccountsResponse(
        linked_accounts=[LinkedAccountPublic.model_validate(acc) for acc in linked],
        available_providers=available,
    )


class InitiateLinkResponse(BaseModel):
    """Response containing OAuth URL for account linking"""
    auth_url: str
    provider: str


@router.post("/link/{provider}", response_model=InitiateLinkResponse)
async def initiate_link(
    provider: str,
    current_user: CurrentUser,
    session: SessionDep,
):
    """
    Initiate OAuth flow to link a new provider account.
    Returns OAuth URL that frontend should redirect to.
    """
    try:
        provider_enum = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be one of: google, github, facebook"
        )

    # Check if already linked
    service = LinkedAccountService(session)
    existing = service.get_linked_account_by_provider(current_user.id, provider_enum)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{provider.title()} account is already linked"
        )

    # Generate state with link mode flag - use shared OAuth state store
    state = secrets.token_urlsafe(32)
    set_oauth_state(state, provider.lower(), mode="link", user_id=str(current_user.id))

    # Use shared OAuth callback URL (already registered with providers)
    callback_url = settings.oauth_callback_url

    # Build OAuth URL based on provider
    if provider_enum == OAuthProvider.GOOGLE:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    elif provider_enum == OAuthProvider.GITHUB:
        if not GITHUB_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth not configured"
            )
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": callback_url,
            "scope": "user:email",
            "state": state,
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    elif provider_enum == OAuthProvider.FACEBOOK:
        if not FACEBOOK_APP_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Facebook OAuth not configured"
            )
        params = {
            "client_id": FACEBOOK_APP_ID,
            "redirect_uri": callback_url,
            "scope": "email,public_profile",
            "state": state,
            "response_type": "code",
        }
        auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}"
        )

    logger.info(f"User {current_user.id} initiating {provider} link")
    return InitiateLinkResponse(auth_url=auth_url, provider=provider.lower())


@router.post("/unlink", response_model=UnlinkAccountResponse)
def unlink_account(
    unlink_data: UnlinkAccountRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> UnlinkAccountResponse:
    """Unlink an OAuth account from current user."""
    service = LinkedAccountService(session)

    # Check if this is the last login method
    linked = service.get_linked_accounts(current_user.id)
    has_password = current_user.hashed_password is not None
    # acc.provider is string, unlink_data.provider is enum
    other_providers = [acc for acc in linked if acc.provider != unlink_data.provider.value]

    if not has_password and len(other_providers) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink the last login method. Add a password first."
        )

    remaining = service.unlink_account(current_user.id, unlink_data.provider)

    return UnlinkAccountResponse(
        message=f"{unlink_data.provider.value.title()} account unlinked successfully",
        remaining_providers=remaining,
    )
