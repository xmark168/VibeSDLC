"""
Artifact Service - Manages agent-produced artifacts.

Provides CRUD operations for artifacts with versioning support.
"""

import logging
import json
import os
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.models import Artifact, ArtifactType, ArtifactStatus


logger = logging.getLogger(__name__)


class ArtifactService:
    """Service for managing agent artifacts"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_artifact(
        self,
        project_id: UUID,
        agent_id: UUID,
        agent_name: str,
        artifact_type: ArtifactType,
        title: str,
        content: dict,
        description: str = None,
        save_to_file: bool = True,
        tags: List[str] = None
    ) -> Artifact:
        """Create a new artifact.
        
        Args:
            project_id: Project ID
            agent_id: Agent ID
            agent_name: Agent name
            artifact_type: Type of artifact
            title: Artifact title
            content: Structured content dict
            description: Optional description
            save_to_file: Whether to save to file system
            tags: Optional tags for categorization
            
        Returns:
            Created Artifact instance
        """
        artifact = Artifact(
            project_id=project_id,
            agent_id=agent_id,
            agent_name=agent_name,
            artifact_type=artifact_type,
            title=title,
            description=description,
            content=content,
            status=ArtifactStatus.DRAFT,
            tags=tags or []
        )
        
        # Save to file system
        if save_to_file:
            try:
                file_path = self._save_to_workspace(project_id, artifact)
                artifact.file_path = file_path
                logger.info(f"Saved artifact to file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to save artifact to file: {e}")
                # Continue anyway - DB save is more important
        
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        
        logger.info(
            f"Created artifact: {artifact_type.value} '{title}' "
            f"(id={artifact.id}, agent={agent_name})"
        )
        
        return artifact
    
    def _save_to_workspace(self, project_id: UUID, artifact: Artifact) -> str:
        """Save artifact content to file system.
        
        Args:
            project_id: Project ID
            artifact: Artifact to save
            
        Returns:
            Relative file path
        """
        # Create workspace directory
        workspace_dir = f"projects/{project_id}/artifacts"
        os.makedirs(workspace_dir, exist_ok=True)
        
        # Generate filename based on type and timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{artifact.artifact_type.value}_{timestamp}_v{artifact.version}.json"
        file_path = os.path.join(workspace_dir, filename)
        
        # Save as JSON with pretty formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "artifact_id": str(artifact.id),
                    "title": artifact.title,
                    "artifact_type": artifact.artifact_type.value,
                    "agent_name": artifact.agent_name,
                    "version": artifact.version,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "content": artifact.content
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        
        return file_path
    
    def get_artifact(self, artifact_id: UUID) -> Optional[Artifact]:
        """Get artifact by ID."""
        return self.session.get(Artifact, artifact_id)
    
    def get_project_artifacts(
        self,
        project_id: UUID,
        artifact_type: ArtifactType = None,
        status: ArtifactStatus = None,
        limit: int = 100
    ) -> List[Artifact]:
        """Get artifacts for a project.
        
        Args:
            project_id: Project ID
            artifact_type: Optional filter by type
            status: Optional filter by status
            limit: Max results
            
        Returns:
            List of artifacts
        """
        query = select(Artifact).where(Artifact.project_id == project_id)
        
        if artifact_type:
            query = query.where(Artifact.artifact_type == artifact_type)
        if status:
            query = query.where(Artifact.status == status)
        
        query = query.order_by(Artifact.created_at.desc()).limit(limit)
        
        return list(self.session.exec(query).all())
    
    def create_version(
        self,
        artifact_id: UUID,
        new_content: dict,
        description: str = None
    ) -> Artifact:
        """Create a new version of an existing artifact.
        
        Args:
            artifact_id: Original artifact ID
            new_content: Updated content
            description: Optional description of changes
            
        Returns:
            New artifact version
        """
        original = self.session.get(Artifact, artifact_id)
        if not original:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        # Archive old version
        original.status = ArtifactStatus.ARCHIVED
        self.session.add(original)
        
        # Create new version
        new_artifact = Artifact(
            project_id=original.project_id,
            agent_id=original.agent_id,
            agent_name=original.agent_name,
            artifact_type=original.artifact_type,
            title=original.title,
            description=description or original.description,
            content=new_content,
            version=original.version + 1,
            parent_artifact_id=artifact_id,
            status=ArtifactStatus.DRAFT,
            tags=original.tags
        )
        
        self.session.add(new_artifact)
        self.session.commit()
        self.session.refresh(new_artifact)
        
        logger.info(
            f"Created artifact version {new_artifact.version} from {artifact_id}"
        )
        
        return new_artifact
    
    def update_status(
        self,
        artifact_id: UUID,
        status: ArtifactStatus,
        reviewed_by_user_id: UUID = None,
        review_feedback: str = None
    ) -> Artifact:
        """Update artifact status (approve/reject).
        
        Args:
            artifact_id: Artifact ID
            status: New status
            reviewed_by_user_id: User who reviewed
            review_feedback: Optional feedback
            
        Returns:
            Updated artifact
        """
        artifact = self.session.get(Artifact, artifact_id)
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        artifact.status = status
        artifact.reviewed_at = datetime.now(timezone.utc)
        
        if reviewed_by_user_id:
            artifact.reviewed_by_user_id = reviewed_by_user_id
        if review_feedback:
            artifact.review_feedback = review_feedback
        
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        
        logger.info(f"Updated artifact {artifact_id} status to {status.value}")
        
        return artifact
    
    def get_latest_version(
        self,
        project_id: UUID,
        artifact_type: ArtifactType,
        title: str = None
    ) -> Optional[Artifact]:
        """Get the latest version of an artifact.
        
        Args:
            project_id: Project ID
            artifact_type: Artifact type
            title: Optional title filter
            
        Returns:
            Latest artifact version or None
        """
        query = select(Artifact).where(
            Artifact.project_id == project_id,
            Artifact.artifact_type == artifact_type,
            Artifact.status != ArtifactStatus.ARCHIVED
        )
        
        if title:
            query = query.where(Artifact.title == title)
        
        # Order by created_at desc to get the truly latest artifact
        query = query.order_by(Artifact.created_at.desc()).limit(1)
        
        result = self.session.exec(query).first()
        if result:
            logger.info(f"[ArtifactService] get_latest_version: found {artifact_type.value} artifact {result.id} (created_at={result.created_at})")
        return result
    
    def delete_by_type(
        self,
        project_id: UUID,
        artifact_type: ArtifactType
    ) -> int:
        """Delete all artifacts of a type for a project.
        
        Args:
            project_id: Project ID
            artifact_type: Type of artifacts to delete
            
        Returns:
            Number of artifacts deleted
        """
        query = select(Artifact).where(
            Artifact.project_id == project_id,
            Artifact.artifact_type == artifact_type
        )
        
        artifacts = list(self.session.exec(query).all())
        count = len(artifacts)
        
        for artifact in artifacts:
            self.session.delete(artifact)
        
        self.session.commit()
        
        logger.info(
            f"[ArtifactService] delete_by_type: deleted {count} {artifact_type.value} "
            f"artifacts for project {project_id}"
        )
        
        return count
