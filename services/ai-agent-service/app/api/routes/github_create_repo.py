"""GitHub repository creation endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.service.github_app_client import GitHubAppClient
from app.api.service.github.create_repo_from_template import create_repo_from_template
from app.core.config import settings
from app.models import GitHubInstallation
from app.schemas import (
    CreateRepoFromTemplateRequest,
    CreateRepoFromTemplateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


@router.post(
    "/create-repo-from-template",
    response_model=CreateRepoFromTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repo_from_template_endpoint(
    request: CreateRepoFromTemplateRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> CreateRepoFromTemplateResponse:
    """
    Create a new GitHub repository from a template.
    
    This endpoint allows authenticated users to create a new repository
    based on an existing template repository using their GitHub App installation.
    
    Args:
        request: Request containing template info and new repo details
        current_user: Current authenticated user
        session: Database session
    
    Returns:
        CreateRepoFromTemplateResponse with repository creation details
        
    Raises:
        HTTPException: If installation not found, user lacks permissions, or GitHub API fails
    """
    try:
        # Validate GitHub installation exists and belongs to current user
        statement = select(GitHubInstallation).where(
            GitHubInstallation.installation_id == request.github_installation_id
        )
        installation = session.exec(statement).first()
        if not installation:
            logger.warning(
                f"GitHub installation {request.github_installation_id} not found for user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub installation not found",
            )

        # Check installation ownership
        if installation.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to use installation {request.github_installation_id} "
                f"owned by {installation.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this GitHub installation",
            )
        
        logger.info(
            f"Creating repository from template: {request.template_owner}/{request.template_repo} "
            f"-> {request.new_repo_name} (user: {current_user.id})"
        )

        # Initialize GitHub client using the installation
        github_app_client = GitHubAppClient(
            app_id=settings.GITHUB_APP_ID,
            installation_id=installation.installation_id,
            private_key=settings.GITHUB_APP_PRIVATE_KEY if settings.GITHUB_APP_PRIVATE_KEY else None,
            private_key_path=settings.GITHUB_APP_PRIVATE_KEY_PATH if hasattr(settings, 'GITHUB_APP_PRIVATE_KEY_PATH') and settings.GITHUB_APP_PRIVATE_KEY_PATH else None,
            session=session,
        )

        # Get GitHub client for the specific installation
        github_client = github_app_client.get_github()
        
        # Create repository from template
        template_full_name = f"{request.template_owner}/{request.template_repo}"
        result = create_repo_from_template(
            github_client=github_client,
            template_repo_name=template_full_name,
            new_repo_name=request.new_repo_name,
            description=request.new_repo_description,
            is_private=request.is_private,
        )
        
        if not result:
            logger.error(f"Failed to create repository from template: {template_full_name}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create repository from template",
            )
        
        if not result.get("success", False):
            error_msg = result.get("message", "Unknown error occurred")
            logger.error(f"Repository creation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        
        logger.info(
            f"Successfully created repository: {result.get('repository_full_name')} "
            f"from template {template_full_name} (user: {current_user.id})"
        )
        
        return CreateRepoFromTemplateResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating repository from template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the repository",
        )

