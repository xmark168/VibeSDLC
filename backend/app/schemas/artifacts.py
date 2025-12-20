"""Artifact-related schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from app.models.base import ArtifactStatus


class ArtifactResponse(BaseModel):
    """Artifact response schema."""
    id: UUID
    project_id: UUID
    agent_id: Optional[UUID]
    agent_name: str
    artifact_type: str
    title: str
    description: Optional[str]
    content: dict
    file_path: Optional[str]
    version: int
    parent_artifact_id: Optional[UUID]
    status: str
    reviewed_by_user_id: Optional[UUID]
    reviewed_at: Optional[datetime]
    review_feedback: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ArtifactListResponse(BaseModel):
    """List of artifacts response."""
    artifacts: List[ArtifactResponse]
    total: int


class UpdateArtifactStatusRequest(BaseModel):
    """Request to update artifact status."""
    status: ArtifactStatus
    feedback: Optional[str] = None
