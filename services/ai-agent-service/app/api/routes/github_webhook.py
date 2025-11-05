"""GitHub App webhook endpoints."""

import logging
import hmac
import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app import crud
from app.api.deps import SessionDep, CurrentUser
from app.core.config import settings
from app.models import GitHubInstallation, GitHubAccountType
from app.schemas import GitHubInstallationCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


def verify_github_webhook_signature(request_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.error("GITHUB_WEBHOOK_SECRET not configured in settings")
        return False

    # Log secret info (first/last 4 chars only for security)
    secret = settings.GITHUB_WEBHOOK_SECRET
    logger.info(
        f"Webhook verification - Secret length: {len(secret)}, "
        f"starts with: {secret[:4]}..., ends with: ...{secret[-4:]}"
    )

    expected_signature = "sha256=" + hmac.new(
        secret.encode('utf-8'),
        request_body,
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(signature, expected_signature)

    # Always log for debugging (use WARNING to see in production)
    logger.warning(
        f"Signature verification:\n"
        f"  Received:  {signature}\n"
        f"  Expected:  {expected_signature}\n"
        f"  Body size: {len(request_body)} bytes\n"
        f"  Match:     {is_valid}"
    )

    return is_valid


@router.post("/webhook")
async def github_webhook(
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    """
    Handle GitHub App webhook events.

    Supported events:
    - installation.created: User installs the GitHub App
    - installation.deleted: User uninstalls the GitHub App
    - installation_repositories.added: User adds repositories to the app
    - installation_repositories.removed: User removes repositories from the app
    """
    # Get request body (only once!)
    body = await request.body()

    # Get signature - MUST use X-Hub-Signature-256 (not the old SHA1 version)
    signature = (
        request.headers.get("X-Hub-Signature-256") or
        request.headers.get("x-hub-signature-256") or
        ""
    )

    logger.info(f"Signature header (X-Hub-Signature-256): {signature[:50] if signature else 'NOT FOUND'}...")

    # Verify signature if present, or warn if missing
    if signature:
        if not verify_github_webhook_signature(body, signature):
            logger.warning(
                f"Invalid GitHub webhook signature. "
                f"Expected signature format: sha256=..., "
                f"Received: {signature[:20] if len(signature) > 20 else signature}... "
                f"Body length: {len(body)}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    else:
        # No signature header - webhook secret not configured in GitHub App
        logger.error(
            "⚠️  NO SIGNATURE HEADER FOUND! "
            "GitHub webhook secret is not configured in your GitHub App settings. "
            "This is a SECURITY RISK in production! "
            "Please configure webhook secret at: https://github.com/settings/apps"
        )

        # In production, you should reject requests without signature
        # For development/testing, we allow it but log a warning
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook signature required"
            )

    # Parse JSON from body bytes
    try:
        payload = json.loads(body.decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    event_type = request.headers.get("X-GitHub-Event", "")
    action = payload.get("action", "")
    
    logger.info(f"Received GitHub webhook: {event_type} - {action}")
    
    # Handle installation.created event
    if event_type == "installation" and action == "created":
        return await handle_installation_created(payload, session)
    
    # Handle installation.deleted event
    elif event_type == "installation" and action == "deleted":
        return await handle_installation_deleted(payload, session)
    
    # Handle installation_repositories.added event
    elif event_type == "installation_repositories" and action == "added":
        return await handle_repositories_added(payload, session)
    
    # Handle installation_repositories.removed event
    elif event_type == "installation_repositories" and action == "removed":
        return await handle_repositories_removed(payload, session)
    
    # Acknowledge other events
    logger.info(f"Ignoring GitHub webhook event: {event_type}")
    return {"status": "acknowledged"}


async def handle_installation_created(
    payload: dict[str, Any], session: Session
) -> dict[str, Any]:
    """Handle GitHub App installation.created event."""
    try:
        from app.models import GitHubInstallationStatus

        installation = payload.get("installation", {})
        sender = payload.get("sender", {})
        repositories = payload.get("repositories", [])

        installation_id = installation.get("id")
        account_login = installation.get("account", {}).get("login")
        account_type = installation.get("account", {}).get("type")

        if not all([installation_id, account_login, account_type]):
            logger.error("Missing required fields in installation.created event")
            raise ValueError("Missing required fields")

        # Convert account_type to enum
        try:
            account_type_enum = GitHubAccountType(account_type)
        except ValueError:
            logger.error(f"Invalid account type: {account_type}")
            raise ValueError(f"Invalid account type: {account_type}")

        # Check if installation already exists (by installation_id OR by account_login with DELETED status)
        existing_by_id = crud.github_installation.get_github_installation_by_installation_id(
            session, installation_id
        )

        # Also check for deleted installations by this user that can be reactivated
        from sqlmodel import select
        from app.models import GitHubInstallation
        deleted_installation = session.exec(
            select(GitHubInstallation).where(
                GitHubInstallation.account_login == account_login,
                GitHubInstallation.account_status == GitHubInstallationStatus.DELETED
            )
        ).first()

        # Case 1: Reinstall - Found a DELETED installation for this account
        if deleted_installation and not existing_by_id:
            logger.info(
                f"Reactivating deleted installation for {account_login} "
                f"(db_id: {deleted_installation.id}) with new installation_id: {installation_id}"
            )
            deleted_installation.installation_id = installation_id
            deleted_installation.account_type = account_type_enum
            deleted_installation.account_status = GitHubInstallationStatus.INSTALLED
            deleted_installation.repositories = {
                "repositories": [
                    {
                        "id": repo.get("id"),
                        "name": repo.get("name"),
                        "full_name": repo.get("full_name"),
                        "url": repo.get("html_url"),
                        "private": repo.get("private"),
                    }
                    for repo in repositories
                ]
            }
            session.add(deleted_installation)
            session.commit()
            logger.info(f"Reactivated GitHub installation {installation_id}")
            return {
                "status": "reactivated",
                "installation_id": installation_id,
                "db_id": str(deleted_installation.id)
            }

        # Case 2: Update existing installation
        if existing_by_id:
            logger.info(f"Installation {installation_id} already exists, updating details...")
            existing_by_id.account_login = account_login
            existing_by_id.account_type = account_type_enum
            existing_by_id.account_status = GitHubInstallationStatus.INSTALLED
            existing_by_id.repositories = {
                "repositories": [
                    {
                        "id": repo.get("id"),
                        "name": repo.get("name"),
                        "full_name": repo.get("full_name"),
                        "url": repo.get("html_url"),
                        "private": repo.get("private"),
                    }
                    for repo in repositories
                ]
            }
            session.add(existing_by_id)
            session.commit()
            logger.info(f"Updated GitHub installation {installation_id}")
            return {
                "status": "updated",
                "installation_id": installation_id,
                "db_id": str(existing_by_id.id)
            }

        # Case 3: New installation (first time install)
        logger.warning(
            f"Installation {installation_id} received via webhook but not yet linked to user. "
            f"Waiting for callback endpoint to be called."
        )

        installation_create = GitHubInstallationCreate(
            installation_id=installation_id,
            account_login=account_login,
            account_type=account_type_enum,
            account_status=GitHubInstallationStatus.PENDING,
            repositories={
                "repositories": [
                    {
                        "id": repo.get("id"),
                        "name": repo.get("name"),
                        "full_name": repo.get("full_name"),
                        "url": repo.get("html_url"),
                        "private": repo.get("private"),
                    }
                    for repo in repositories
                ]
            },
            user_id=None,  # Will be set by callback endpoint
        )

        db_installation = crud.github_installation.create_github_installation(
            session, installation_create
        )

        logger.info(f"Created placeholder GitHub installation: {db_installation.id}")
        return {
            "status": "created_placeholder",
            "installation_id": installation_id,
            "db_id": str(db_installation.id),
            "note": "Installation created but not yet linked to user. Waiting for callback."
        }

    except Exception as e:
        logger.error(f"Error handling installation.created: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


async def handle_installation_deleted(
    payload: dict[str, Any], session: Session
) -> dict[str, Any]:
    """Handle GitHub App installation.deleted event."""
    try:
        installation = payload.get("installation", {})
        installation_id = installation.get("id")

        if not installation_id:
            logger.error("Missing installation_id in installation.deleted event")
            raise ValueError("Missing installation_id")

        # Get installation record
        db_installation = crud.github_installation.get_github_installation_by_installation_id(
            session, installation_id
        )

        if not db_installation:
            logger.warning(f"Installation {installation_id} not found in database")
            return {"status": "not_found", "installation_id": installation_id}

        # Instead of deleting, set installation_id to NULL and status to DELETED
        from app.models import GitHubInstallationStatus
        db_installation.installation_id = None
        db_installation.account_status = GitHubInstallationStatus.DELETED
        session.add(db_installation)
        session.commit()

        logger.info(
            f"Marked GitHub installation {installation_id} as DELETED "
            f"(db_id: {db_installation.id}, user_id: {db_installation.user_id})"
        )
        return {
            "status": "marked_deleted",
            "installation_id": installation_id,
            "db_id": str(db_installation.id)
        }

    except Exception as e:
        logger.error(f"Error handling installation.deleted: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


async def handle_repositories_added(
    payload: dict[str, Any], session: Session
) -> dict[str, Any]:
    """Handle GitHub App installation_repositories.added event."""
    try:
        installation = payload.get("installation", {})
        repositories_added = payload.get("repositories_added", [])
        
        installation_id = installation.get("id")
        
        if not installation_id:
            logger.error("Missing installation_id in installation_repositories.added event")
            raise ValueError("Missing installation_id")
        
        # Get installation record
        db_installation = crud.github_installation.get_github_installation_by_installation_id(
            session, installation_id
        )
        
        if not db_installation:
            logger.warning(f"Installation not found: {installation_id}")
            return {"status": "not_found", "installation_id": installation_id}
        
        # Update repositories
        if not db_installation.repositories:
            db_installation.repositories = {"repositories": []}
        
        existing_repos = db_installation.repositories.get("repositories", [])
        for repo in repositories_added:
            repo_data = {
                "id": repo.get("id"),
                "name": repo.get("name"),
                "full_name": repo.get("full_name"),
                "url": repo.get("html_url"),
                "private": repo.get("private"),
            }
            # Avoid duplicates
            if not any(r.get("id") == repo_data["id"] for r in existing_repos):
                existing_repos.append(repo_data)
        
        db_installation.repositories["repositories"] = existing_repos
        session.add(db_installation)
        session.commit()
        
        logger.info(f"Added {len(repositories_added)} repositories to installation {installation_id}")
        return {
            "status": "updated",
            "installation_id": installation_id,
            "repositories_added": len(repositories_added)
        }
    
    except Exception as e:
        logger.error(f"Error handling installation_repositories.added: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


async def handle_repositories_removed(
    payload: dict[str, Any], session: Session
) -> dict[str, Any]:
    """Handle GitHub App installation_repositories.removed event."""
    try:
        installation = payload.get("installation", {})
        repositories_removed = payload.get("repositories_removed", [])
        
        installation_id = installation.get("id")
        
        if not installation_id:
            logger.error("Missing installation_id in installation_repositories.removed event")
            raise ValueError("Missing installation_id")
        
        # Get installation record
        db_installation = crud.github_installation.get_github_installation_by_installation_id(
            session, installation_id
        )
        
        if not db_installation:
            logger.warning(f"Installation not found: {installation_id}")
            return {"status": "not_found", "installation_id": installation_id}
        
        # Update repositories
        if db_installation.repositories:
            existing_repos = db_installation.repositories.get("repositories", [])
            removed_ids = {repo.get("id") for repo in repositories_removed}
            db_installation.repositories["repositories"] = [
                r for r in existing_repos if r.get("id") not in removed_ids
            ]
            session.add(db_installation)
            session.commit()
        
        logger.info(f"Removed {len(repositories_removed)} repositories from installation {installation_id}")
        return {
            "status": "updated",
            "installation_id": installation_id,
            "repositories_removed": len(repositories_removed)
        }
    
    except Exception as e:
        logger.error(f"Error handling installation_repositories.removed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/callback")
async def github_callback(
    installation_id: int,
    setup_action: str | None = None,
    session: SessionDep = None,
) -> RedirectResponse:
    """
    Handle GitHub App OAuth callback.

    This endpoint is called by GitHub after user installs the GitHub App.
    GitHub redirects here WITHOUT authentication, so we create a pending installation.

    Query Parameters:
    - installation_id: GitHub's installation ID (required)
    - setup_action: "install" or "update" (optional)

    Flow:
    1. User clicks "Install GitHub App" button
    2. Redirects to GitHub App installation page
    3. User installs app on GitHub
    4. GitHub redirects to this endpoint with installation_id
    5. Backend creates pending installation (user_id = NULL)
    6. Webhook updates installation details
    7. Frontend links installation with current user

    Note: This endpoint does NOT require authentication because GitHub
    redirects here without JWT token. Installation is created as "pending"
    and will be linked to user later.
    """
    try:
        if not installation_id:
            logger.error("Missing installation_id in GitHub callback")
            return RedirectResponse(
                url=f"{settings.FRONTEND_HOST}/projects?error=missing_installation_id",
                status_code=status.HTTP_302_FOUND
            )

        # Check if installation already exists
        existing = crud.github_installation.get_github_installation_by_installation_id(
            session, installation_id
        )

        if existing:
            logger.info(
                f"Installation {installation_id} already exists (user_id: {existing.user_id}). "
                f"Webhook will update details."
            )
            # Installation already exists, webhook will update details
            # Just redirect to frontend
            return RedirectResponse(
                url=f"{settings.FRONTEND_HOST}/projects?github_installation=exists&installation_id={installation_id}",
                status_code=status.HTTP_302_FOUND
            )

        # Create new PENDING installation (user_id = NULL)
        # Webhook will update details, frontend will link with user
        from app.models import GitHubInstallationStatus
        installation_create = GitHubInstallationCreate(
            installation_id=installation_id,
            account_login="",  # Will be updated by webhook
            account_type=GitHubAccountType.USER,  # Default, will be updated by webhook
            account_status=GitHubInstallationStatus.PENDING,
            repositories={"repositories": []},  # Empty for now, will be updated by webhook
            user_id=None,  # PENDING - will be linked by frontend or user action
        )

        db_installation = crud.github_installation.create_github_installation(
            session, installation_create
        )

        logger.info(
            f"Created PENDING GitHub installation {installation_id} "
            f"(db_id: {db_installation.id}). Waiting for webhook and user linking."
        )

        return RedirectResponse(
            url=f"{settings.FRONTEND_HOST}/projects?github_installation=pending&installation_id={installation_id}",
            status_code=status.HTTP_302_FOUND
        )

    except Exception as e:
        logger.error(f"Error handling GitHub callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.FRONTEND_HOST}/projects?error=callback_failed&message={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/link-installation")
async def link_installation_to_user(
    installation_id: int,
    current_user: CurrentUser = None,
    session: SessionDep = None,
) -> dict[str, Any]:
    """
    Link a pending GitHub installation with the current user.

    This endpoint is called by frontend after user confirms linking.

    Request Body:
    - installation_id: GitHub installation ID to link

    Response:
    - status: "linked" or "error"
    - installation_id: GitHub installation ID
    - db_id: Database installation ID
    - message: Status message

    Flow:
    1. User installs GitHub App (callback creates pending installation)
    2. Frontend shows "Link with your account?" prompt
    3. User clicks "Link"
    4. Frontend calls this endpoint with installation_id
    5. Backend links installation with current user
    6. Frontend shows success message
    """
    try:
        if not installation_id:
            raise ValueError("installation_id is required")

        # Get pending installation
        installation = crud.github_installation.get_github_installation_by_installation_id(
            session, installation_id
        )

        if not installation:
            logger.warning(f"Installation {installation_id} not found")
            return {
                "status": "error",
                "message": f"Installation {installation_id} not found",
                "installation_id": installation_id
            }

        if installation.user_id is not None:
            logger.warning(
                f"Installation {installation_id} already linked to user {installation.user_id}"
            )
            return {
                "status": "error",
                "message": f"Installation already linked to another user",
                "installation_id": installation_id
            }

        # Link installation with current user and set status to INSTALLED
        from app.models import GitHubInstallationStatus
        installation.user_id = current_user.id
        installation.account_status = GitHubInstallationStatus.INSTALLED
        session.add(installation)
        session.commit()

        logger.info(
            f"Linked GitHub installation {installation_id} to user {current_user.id} "
            f"and set status to INSTALLED"
        )

        return {
            "status": "linked",
            "installation_id": installation_id,
            "db_id": str(installation.id),
            "message": "Installation linked successfully"
        }

    except Exception as e:
        logger.error(f"Error linking installation: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "installation_id": installation_id
        }

