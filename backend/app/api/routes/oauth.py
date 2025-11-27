"""OAuth authentication routes for Google, GitHub, Facebook."""

import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.security import create_access_token
from app.models import User
from app.services import UserService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["oauth"])

# In-memory store for OAuth state (sufficient for OAuth flow)
# Note: OAuth state is short-lived (seconds), so Redis is unnecessary
_oauth_state_store: dict[str, dict] = {}


def set_oauth_state(state: str, provider: str):
    """Save OAuth state to in-memory store"""
    import time
    _oauth_state_store[state] = {
        "provider": provider,
        "created_at": time.time()
    }
    logger.info(f"Saved OAuth state: {state} for {provider}")
    # Clean up old states (older than 10 minutes)
    _cleanup_old_states()


def get_oauth_state(state: str) -> str | None:
    """Get OAuth state from in-memory store"""
    state_data = _oauth_state_store.get(state)
    if state_data:
        logger.info(f"Retrieved OAuth state: {state} for {state_data['provider']}")
        return state_data["provider"]
    logger.warning(f"OAuth state not found: {state}")
    return None


def delete_oauth_state(state: str):
    """Delete OAuth state"""
    _oauth_state_store.pop(state, None)
    logger.info(f"Deleted OAuth state: {state}")


def _cleanup_old_states():
    """Remove OAuth states older than 10 minutes"""
    import time
    current_time = time.time()
    expired_states = [
        state for state, data in _oauth_state_store.items()
        if current_time - data["created_at"] > 600  # 10 minutes
    ]
    for state in expired_states:
        _oauth_state_store.pop(state, None)
    if expired_states:
        logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")


# OAuth configurations (add to .env)
GOOGLE_CLIENT_ID = (
    settings.GOOGLE_CLIENT_ID if hasattr(settings, "GOOGLE_CLIENT_ID") else ""
)
GOOGLE_CLIENT_SECRET = (
    settings.GOOGLE_CLIENT_SECRET if hasattr(settings, "GOOGLE_CLIENT_SECRET") else ""
)
GITHUB_CLIENT_ID = (
    settings.GITHUB_CLIENT_ID if hasattr(settings, "GITHUB_CLIENT_ID") else ""
)
GITHUB_CLIENT_SECRET = (
    settings.GITHUB_CLIENT_SECRET if hasattr(settings, "GITHUB_CLIENT_SECRET") else ""
)


@router.get("/auth/google")
async def google_login(request: Request):
    """Redirect to Google OAuth"""
    logger.info(f"Google OAuth initiated from {request.client.host}")

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured. Add GOOGLE_CLIENT_ID to .env",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Save state
    set_oauth_state(state, "google")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": settings.oauth_callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    logger.info(f"Redirecting to Google OAuth: {auth_url[:100]}...")
    return RedirectResponse(auth_url)


@router.get("/auth/github")
async def github_login(request: Request):
    """Redirect to GitHub OAuth"""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth not configured. Add GITHUB_CLIENT_ID to .env",
        )

    state = secrets.token_urlsafe(32)
    set_oauth_state(state, "github")

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": settings.oauth_callback_url,
        "scope": "user:email",
        "state": state,
    }

    auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)


@router.get("/auth/facebook")
async def facebook_login(request: Request):
    """Redirect to Facebook OAuth"""
    FACEBOOK_APP_ID = (
        settings.FACEBOOK_APP_ID if hasattr(settings, "FACEBOOK_APP_ID") else ""
    )

    if not FACEBOOK_APP_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Facebook OAuth not configured. Add FACEBOOK_APP_ID to .env",
        )

    state = secrets.token_urlsafe(32)
    set_oauth_state(state, "facebook")

    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": settings.oauth_callback_url,
        "scope": "email,public_profile",
        "state": state,
        "response_type": "code",
    }

    auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    return RedirectResponse(auth_url)


@router.get("/oauth-callback")
async def oauth_callback(
    code: str,
    state: str,
    response: Response,
    session: SessionDep,
):
    """Handle OAuth callback from providers"""
    logger.info(f"OAuth callback - code: {code[:20]}..., state: {state}")
    
    # Verify state
    provider = get_oauth_state(state)

    if not provider:
        logger.error(f"Invalid OAuth state - Available states: {len(_oauth_state_store)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please try again.",
        )

    # Clean up state immediately after verification
    delete_oauth_state(state)

    try:
        # Add timeout for external API calls
        if provider == "google":
            user_info = await _get_google_user(code)
        elif provider == "github":
            user_info = await _get_github_user(code)
        elif provider == "facebook":
            user_info = await _get_facebook_user(code)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )

        logger.info(f"Successfully retrieved user info from {provider}: {user_info['email']}")

        provider_name = provider.upper()
        
        # Create unique email by adding provider suffix
        # Example: test@gmail.com + GOOGLE → test+google@gmail.com
        original_email = user_info["email"]
        email_parts = original_email.rsplit('@', 1)
        if len(email_parts) == 2:
            unique_email = f"{email_parts[0]}+{provider.lower()}@{email_parts[1]}"
        else:
            unique_email = f"{original_email}+{provider.lower()}"
        
        logger.info(f"Original email: {original_email}, Unique email for DB: {unique_email}")

        # Find or create user with provider-specific email
        user_service = UserService(session)
        user = user_service.get_by_email(unique_email)

        if not user:
            logger.info(f"Creating new user for {provider_name}: {unique_email}")
            user = User(
                email=unique_email,  # Unique email with provider suffix
                full_name=user_info["name"],
                login_provider=provider_name,  # Save provider name: GOOGLE, GITHUB, FACEBOOK
                is_active=True,
                is_locked=False,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Created new user with ID: {user.id} via {provider_name}")
        else:
            logger.info(f"Found existing user: {user.id} for {provider_name}")

        # Create tokens
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            token_type="access",
        )

        refresh_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            token_type="refresh",
        )

        logger.info(f"Created tokens for user {user.id}, redirecting to frontend")

        # Redirect to frontend with tokens in URL
        redirect_url = f"{settings.FRONTEND_HOST}/oauth-success?access_token={access_token}&refresh_token={refresh_token}"
        return RedirectResponse(redirect_url)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"OAuth callback error for provider {provider}: {e}", exc_info=True)
        return RedirectResponse(f"{settings.FRONTEND_HOST}/login?error=oauth_failed")


async def _get_google_user(code: str) -> dict:
    """Exchange Google code for user info"""
    timeout = httpx.Timeout(10.0, connect=5.0)  # 10s total, 5s connect
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Exchange code for token
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.oauth_callback_url,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange Google code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user info
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get Google user info",
            )

        user_data = user_response.json()
        return {
            "email": user_data["email"],
            "name": user_data.get("name", user_data["email"].split("@")[0]),
        }


async def _get_github_user(code: str) -> dict:
    """Exchange GitHub code for user info"""
    timeout = httpx.Timeout(10.0, connect=5.0)  # 10s total, 5s connect
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Exchange code for token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "code": code,
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "redirect_uri": settings.oauth_callback_url,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange GitHub code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get GitHub user info",
            )

        user_data = user_response.json()

        # Get primary email if not public
        email = user_data.get("email")
        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            emails = emails_response.json()
            primary_email = next((e for e in emails if e["primary"]), None)
            email = primary_email["email"] if primary_email else None

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account has no email",
            )

        return {
            "email": email,
            "name": user_data.get("name")
            or user_data.get("login", email.split("@")[0]),
        }


async def _get_facebook_user(code: str) -> dict:
    """Exchange Facebook code for user info"""
    FACEBOOK_APP_ID = (
        settings.FACEBOOK_APP_ID if hasattr(settings, "FACEBOOK_APP_ID") else ""
    )
    FACEBOOK_APP_SECRET = (
        settings.FACEBOOK_APP_SECRET if hasattr(settings, "FACEBOOK_APP_SECRET") else ""
    )

    timeout = httpx.Timeout(10.0, connect=5.0)  # 10s total, 5s connect
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Exchange code for token
        token_response = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "code": code,
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "redirect_uri": settings.oauth_callback_url,
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange Facebook code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user info
        user_response = await client.get(
            "https://graph.facebook.com/v18.0/me",
            params={
                "fields": "id,name,email",
                "access_token": access_token,
            },
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get Facebook user info",
            )

        user_data = user_response.json()

        if not user_data.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Facebook account has no email. Please grant email permission.",
            )

        return {
            "email": user_data["email"],
            "name": user_data.get("name", user_data["email"].split("@")[0]),
        }
