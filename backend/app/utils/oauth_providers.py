"""OAuth provider integrations."""

import httpx
import logging
from typing import Dict
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


async def get_google_user_info(code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict:
    """Exchange Google OAuth code for user information.
    
    Args:
        code: Authorization code from Google
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_uri: OAuth callback URL
        
    Returns:
        Dictionary with user info (id, email, name, avatar_url)
        
    Raises:
        HTTPException: If OAuth flow fails
    """
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Exchange code for access token
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            logger.error(f"Google token exchange failed: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange Google code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user information
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            logger.error(f"Google user info failed: {user_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get Google user info",
            )

        user_data = user_response.json()
        return {
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data.get("name", user_data["email"].split("@")[0]),
            "avatar_url": user_data.get("picture"),
        }


async def get_github_user_info(code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict:
    """Exchange GitHub OAuth code for user information.
    
    Args:
        code: Authorization code from GitHub
        client_id: GitHub OAuth client ID
        client_secret: GitHub OAuth client secret
        redirect_uri: OAuth callback URL
        
    Returns:
        Dictionary with user info (id, email, name, avatar_url)
        
    Raises:
        HTTPException: If OAuth flow fails
    """
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Exchange code for access token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            logger.error(f"GitHub token exchange failed: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange GitHub code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user information
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            logger.error(f"GitHub user info failed: {user_response.text}")
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
            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary_email = next((e for e in emails if e["primary"]), None)
                email = primary_email["email"] if primary_email else None

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account has no email",
            )

        return {
            "id": str(user_data["id"]),
            "email": email,
            "name": user_data.get("name") or user_data.get("login", email.split("@")[0]),
            "avatar_url": user_data.get("avatar_url"),
        }


async def get_facebook_user_info(code: str, app_id: str, app_secret: str, redirect_uri: str) -> Dict:
    """Exchange Facebook OAuth code for user information.
    
    Args:
        code: Authorization code from Facebook
        app_id: Facebook App ID
        app_secret: Facebook App Secret
        redirect_uri: OAuth callback URL
        
    Returns:
        Dictionary with user info (id, email, name, avatar_url)
        
    Raises:
        HTTPException: If OAuth flow fails
    """
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Exchange code for access token
        token_response = await client.get(
            "https://graph.facebook.com/v12.0/oauth/access_token",
            params={
                "code": code,
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
            },
        )

        if token_response.status_code != 200:
            logger.error(f"Facebook token exchange failed: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange Facebook code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user information
        user_response = await client.get(
            "https://graph.facebook.com/me",
            params={
                "fields": "id,name,email,picture.type(large)",
                "access_token": access_token,
            },
        )

        if user_response.status_code != 200:
            logger.error(f"Facebook user info failed: {user_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get Facebook user info",
            )

        user_data = user_response.json()

        if not user_data.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Facebook account has no email",
            )

        avatar_url = None
        if "picture" in user_data and "data" in user_data["picture"]:
            avatar_url = user_data["picture"]["data"].get("url")

        return {
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data.get("name", user_data["email"].split("@")[0]),
            "avatar_url": avatar_url,
        }
