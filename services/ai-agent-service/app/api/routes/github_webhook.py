"""GitHub App webhook endpoints."""

import logging
import hmac
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app import crud
from app.api.deps import SessionDep
from app.core.config import settings
from app.models import GitHubInstallation, GitHubAccountType
from app.schemas import GitHubInstallationCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/github", tags=["github"])


def verify_github_webhook_signature(request_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured")
        return False

    expected_signature = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        request_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


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
    # Get request body
    body = await request.body()
    
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_webhook_signature(body, signature):
        logger.warning("Invalid GitHub webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse JSON
    try:
        payload = await request.json()
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
        
        # Check if installation already exists
        existing = crud.github_installation.get_github_installation_by_installation_id(
            session, installation_id
        )
        if existing:
            logger.info(f"Installation {installation_id} already exists, updating...")
            # Update repositories
            existing.repositories = {
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
            session.add(existing)
            session.commit()
            return {"status": "updated", "installation_id": installation_id}
        
        # Get user by GitHub login (sender)
        sender_login = sender.get("login")
        user = crud.user.get_user_by_email(session, sender_login)
        
        if not user:
            logger.warning(f"User not found for GitHub login: {sender_login}")
            # For now, we'll skip creating installation if user doesn't exist
            # In production, you might want to create a user or handle this differently
            return {
                "status": "skipped",
                "reason": "User not found",
                "installation_id": installation_id
            }
        
        # Create installation record
        installation_create = GitHubInstallationCreate(
            installation_id=installation_id,
            account_login=account_login,
            account_type=account_type_enum,
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
            user_id=user.id,
        )
        
        db_installation = crud.github_installation.create_github_installation(
            session, installation_create
        )
        
        logger.info(f"Created GitHub installation: {db_installation.id}")
        return {
            "status": "created",
            "installation_id": installation_id,
            "db_id": str(db_installation.id)
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
        
        # Delete installation record
        deleted = crud.github_installation.delete_github_installation_by_installation_id(
            session, installation_id
        )
        
        if deleted:
            logger.info(f"Deleted GitHub installation: {installation_id}")
            return {"status": "deleted", "installation_id": installation_id}
        else:
            logger.warning(f"Installation not found: {installation_id}")
            return {"status": "not_found", "installation_id": installation_id}
    
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

