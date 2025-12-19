"""
Artifact API endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, SessionDep
from app.models import User, Artifact, ArtifactType, ArtifactStatus
from app.services.artifact_service import ArtifactService
from app.schemas.artifacts import (
    ArtifactResponse,
    ArtifactListResponse,
    UpdateArtifactStatusRequest,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


# ==================== ENDPOINTS ====================

@router.get("/projects/{project_id}/artifacts", response_model=ArtifactListResponse)
async def list_project_artifacts(
    project_id: UUID,
    session: SessionDep,
    _: User = Depends(get_current_user),
    artifact_type: Optional[ArtifactType] = Query(None, description="Filter by artifact type"),
    status: Optional[ArtifactStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
):
    """List all artifacts for a project."""
    try:
        service = ArtifactService(session)
        artifacts = service.get_project_artifacts(
            project_id=project_id,
            artifact_type=artifact_type,
            status=status,
            limit=limit
        )
        
        return ArtifactListResponse(
            artifacts=[ArtifactResponse.model_validate(a) for a in artifacts],
            total=len(artifacts)
        )
    
    except Exception as e:
        logger.error(f"Error listing artifacts: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list artifacts: {str(e)}")


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get artifact details.
    
    Args:
        artifact_id: Artifact UUID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        Artifact details
    """
    try:
        service = ArtifactService(session)
        artifact = service.get_artifact(artifact_id)
        
        if not artifact:
            raise HTTPException(404, "Artifact not found")
        
        return ArtifactResponse.model_validate(artifact)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting artifact: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get artifact: {str(e)}")


@router.patch("/artifacts/{artifact_id}/status", response_model=ArtifactResponse)
async def update_artifact_status(
    artifact_id: UUID,
    request: UpdateArtifactStatusRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update artifact status (approve/reject).
    
    Args:
        artifact_id: Artifact UUID
        request: Update request with status and optional feedback
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated artifact
    """
    try:
        service = ArtifactService(session)
        artifact = service.update_status(
            artifact_id=artifact_id,
            status=request.status,
            reviewed_by_user_id=current_user.id,
            review_feedback=request.feedback
        )
        
        logger.info(
            f"User {current_user.email} updated artifact {artifact_id} "
            f"status to {request.status.value}"
        )
        
        return ArtifactResponse.model_validate(artifact)
    
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error updating artifact status: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update artifact status: {str(e)}")


@router.post("/artifacts/{artifact_id}/version", response_model=ArtifactResponse)
async def create_artifact_version(
    artifact_id: UUID,
    new_content: dict,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    description: Optional[str] = None,
):
    """Create a new version of an artifact.
    
    Args:
        artifact_id: Original artifact UUID
        new_content: Updated content
        description: Optional description of changes
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        New artifact version
    """
    try:
        service = ArtifactService(session)
        new_artifact = service.create_version(
            artifact_id=artifact_id,
            new_content=new_content,
            description=description
        )
        
        logger.info(
            f"User {current_user.email} created version {new_artifact.version} "
            f"of artifact {artifact_id}"
        )
        
        return ArtifactResponse.model_validate(new_artifact)
    
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error creating artifact version: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create artifact version: {str(e)}")


@router.get("/projects/{project_id}/artifacts/latest", response_model=Optional[ArtifactResponse])
async def get_latest_artifact(
    project_id: UUID,
    artifact_type: ArtifactType,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    title: Optional[str] = Query(None, description="Filter by title"),
):
    """Get the latest version of an artifact.
    
    Args:
        project_id: Project UUID
        artifact_type: Artifact type
        title: Optional title filter
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        Latest artifact version or None
    """
    try:
        service = ArtifactService(session)
        artifact = service.get_latest_version(
            project_id=project_id,
            artifact_type=artifact_type,
            title=title
        )
        
        if not artifact:
            return None
        
        return ArtifactResponse.model_validate(artifact)
    
    except Exception as e:
        logger.error(f"Error getting latest artifact: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get latest artifact: {str(e)}")
