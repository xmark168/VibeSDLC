"""GitHub repository linking endpoints."""

import logging
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.service.github_app_client import GitHubAppClient
from app.core.config import settings
from app.models import Project, GitHubInstallation
from app.schemas import (
    GitHubRepositoriesPublic,
    GitHubRepository,
    ProjectGitHubLink,
    ProjectPublic,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/github", tags=["github"])


@router.get("/repositories", response_model=GitHubRepositoriesPublic)
async def list_github_repositories(
    current_user: CurrentUser,
    session: SessionDep,
    installation_id: UUID | None = None,
    skip: int = 0,
    limit: int = 10,
) -> GitHubRepositoriesPublic:
    """
    List available GitHub repositories for the current user.
    
    If installation_id is provided, list repositories for that specific installation.
    Otherwise, list repositories from all user's installations.
    """
    try:
        repositories = []
        
        if installation_id:
            # Get specific installation
            installation = crud.github_installation.get_github_installation(
                session, installation_id
            )
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="GitHub installation not found"
                )
            
            if installation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this installation"
                )
            
            # Get repositories from installation
            if installation.repositories:
                repos = installation.repositories.get("repositories", [])
                for repo in repos:
                    repositories.append(
                        GitHubRepository(
                            id=repo.get("id"),
                            name=repo.get("name"),
                            full_name=repo.get("full_name"),
                            url=repo.get("url"),
                            description=repo.get("description"),
                            private=repo.get("private", False),
                            owner=installation.account_login,
                        )
                    )
        else:
            # Get repositories from all user's installations
            installations = crud.github_installation.get_github_installations_by_user(
                session, current_user.id, skip=0, limit=100
            )
            
            for installation in installations:
                if installation.repositories:
                    repos = installation.repositories.get("repositories", [])
                    for repo in repos:
                        repositories.append(
                            GitHubRepository(
                                id=repo.get("id"),
                                name=repo.get("name"),
                                full_name=repo.get("full_name"),
                                url=repo.get("url"),
                                description=repo.get("description"),
                                private=repo.get("private", False),
                                owner=installation.account_login,
                            )
                        )
        
        # Apply pagination
        paginated_repos = repositories[skip : skip + limit]
        
        return GitHubRepositoriesPublic(
            data=paginated_repos,
            count=len(repositories)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing GitHub repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing repositories"
        )


@router.post("/projects/{project_id}/link-repository", response_model=ProjectPublic)
async def link_github_repository(
    project_id: UUID,
    link_data: ProjectGitHubLink,
    current_user: CurrentUser,
    session: SessionDep,
) -> ProjectPublic:
    """
    Link a GitHub repository to a project.
    """
    try:
        # Get project
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check ownership
        if project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this project"
            )
        
        # Get installation
        installation = session.get(GitHubInstallation, link_data.github_installation_id)
        if not installation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub installation not found"
            )
        
        # Check installation ownership
        if installation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this installation"
            )
        
        # Check if repository exists in installation
        if installation.repositories:
            repos = installation.repositories.get("repositories", [])
            repo_exists = any(
                r.get("id") == link_data.github_repository_id for r in repos
            )
            if not repo_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Repository not found in this installation"
                )
        
        # Update project
        project.github_repository_id = link_data.github_repository_id
        project.github_repository_name = link_data.github_repository_name
        project.github_installation_id = link_data.github_installation_id
        
        session.add(project)
        session.commit()
        session.refresh(project)
        
        logger.info(f"Linked repository {link_data.github_repository_name} to project {project_id}")
        
        return ProjectPublic.model_validate(project)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking GitHub repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error linking repository"
        )


@router.delete("/projects/{project_id}/unlink-repository", response_model=ProjectPublic)
async def unlink_github_repository(
    project_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> ProjectPublic:
    """
    Unlink a GitHub repository from a project.
    """
    try:
        # Get project
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check ownership
        if project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this project"
            )
        
        # Check if repository is linked
        if not project.github_repository_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No GitHub repository linked to this project"
            )
        
        # Unlink repository
        project.github_repository_id = None
        project.github_repository_name = None
        project.github_installation_id = None
        
        session.add(project)
        session.commit()
        session.refresh(project)
        
        logger.info(f"Unlinked repository from project {project_id}")
        
        return ProjectPublic.model_validate(project)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking GitHub repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error unlinking repository"
        )


@router.get("/installations", response_model=dict[str, Any])
async def list_github_installations(
    current_user: CurrentUser,
    session: SessionDep,
    skip: int = 0,
    limit: int = 10,
) -> dict[str, Any]:
    """
    List all GitHub App installations for the current user.
    """
    try:
        installations = crud.github_installation.get_github_installations_by_user(
            session, current_user.id, skip=skip, limit=limit
        )
        
        total = crud.github_installation.count_github_installations_by_user(
            session, current_user.id
        )
        
        return {
            "data": [
                {
                    "id": str(inst.id),
                    "installation_id": inst.installation_id,
                    "account_login": inst.account_login,
                    "account_type": inst.account_type,
                    "repositories_count": len(inst.repositories.get("repositories", []))
                    if inst.repositories
                    else 0,
                    "created_at": inst.created_at,
                    "updated_at": inst.updated_at,
                }
                for inst in installations
            ],
            "count": total,
        }
    
    except Exception as e:
        logger.error(f"Error listing GitHub installations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing installations"
        )

