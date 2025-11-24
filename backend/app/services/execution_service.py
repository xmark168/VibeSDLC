"""Execution Service - Encapsulates agent execution tracking."""

import asyncio
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import AgentExecution, AgentExecutionStatus


class ExecutionService:
    """Service for agent execution tracking.
    
    Provides async-safe methods for creating and updating execution records
    without blocking the event loop.
    """

    def __init__(self, session: Session):
        self.session = session

    # ===== Async-Safe Execution Management =====

    async def create_execution(
        self,
        project_id: UUID,
        agent_name: str,
        agent_type: str,
        trigger_message_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        task_type: Optional[str] = None,
        task_content_preview: Optional[str] = None,
    ) -> UUID:
        """Create execution record (async-safe, uses thread pool).
        
        Args:
            project_id: Project UUID
            agent_name: Agent name
            agent_type: Agent type/role
            trigger_message_id: Optional message that triggered this
            user_id: Optional user ID
            task_type: Optional task type
            task_content_preview: Optional preview of task content
            
        Returns:
            Created execution ID
        """
        execution = AgentExecution(
            project_id=project_id,
            agent_name=agent_name,
            agent_type=agent_type,
            status=AgentExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            trigger_message_id=trigger_message_id,
            user_id=user_id,
            extra_metadata={
                "task_type": task_type or "unknown",
                "task_content_preview": task_content_preview or "",
            }
        )
        
        # Run in thread pool to avoid blocking event loop
        def _save():
            from app.core.db import engine  # Import here to avoid circular import
            with Session(engine) as db:
                db.add(execution)
                db.commit()
                db.refresh(execution)
            return execution.id
        
        return await asyncio.to_thread(_save)

    async def complete_execution(
        self,
        execution_id: UUID,
        success: bool,
        output: Optional[str] = None,
        structured_data: Optional[dict] = None,
        error: Optional[str] = None,
        error_traceback: Optional[str] = None,
        events: Optional[list] = None,
        duration_ms: Optional[int] = None
    ) -> None:
        """Complete execution record (async-safe, uses thread pool).
        
        Args:
            execution_id: Execution UUID
            success: Whether execution succeeded
            output: Optional output text
            structured_data: Optional structured result data
            error: Optional error message
            error_traceback: Optional error traceback
            events: Optional list of events
            duration_ms: Optional duration in milliseconds
        """
        def _update():
            from app.core.db import engine  # Import here to avoid circular import
            with Session(engine) as db:
                execution = db.get(AgentExecution, execution_id)
                if execution:
                    execution.status = (
                        AgentExecutionStatus.COMPLETED if success 
                        else AgentExecutionStatus.FAILED
                    )
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.duration_ms = duration_ms
                    
                    # Store events
                    if events:
                        execution.extra_metadata = execution.extra_metadata or {}
                        execution.extra_metadata["events"] = events
                        execution.extra_metadata["total_events"] = len(events)
                    
                    # Store result
                    if output or structured_data:
                        execution.result = {
                            "success": success,
                            "output": output[:1000] if output else "",  # Truncate
                            "structured_data": structured_data,
                        }
                    
                    # Store error
                    if error:
                        execution.error_message = error[:1000]  # Truncate
                        execution.error_traceback = error_traceback[:2000] if error_traceback else None
                    
                    db.add(execution)
                    db.commit()
                    return execution.status.value
            return None
        
        await asyncio.to_thread(_update)

    # ===== Synchronous Methods =====

    def get_by_id(self, execution_id: UUID) -> Optional[AgentExecution]:
        """Get execution by ID.
        
        Args:
            execution_id: Execution UUID
            
        Returns:
            Execution or None if not found
        """
        return self.session.get(AgentExecution, execution_id)

    def get_by_project(
        self,
        project_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: Optional[AgentExecutionStatus] = None
    ) -> list[AgentExecution]:
        """Get executions for a project.
        
        Args:
            project_id: Project UUID
            limit: Maximum number of executions
            offset: Number to skip
            status: Optional status filter
            
        Returns:
            List of executions
        """
        statement = (
            select(AgentExecution)
            .where(AgentExecution.project_id == project_id)
            .order_by(AgentExecution.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            statement = statement.where(AgentExecution.status == status)
        return self.session.exec(statement).all()

    def get_by_agent(
        self,
        agent_name: str,
        project_id: Optional[UUID] = None,
        limit: int = 100
    ) -> list[AgentExecution]:
        """Get executions for an agent.
        
        Args:
            agent_name: Agent name
            project_id: Optional project filter
            limit: Maximum number of executions
            
        Returns:
            List of executions
        """
        statement = (
            select(AgentExecution)
            .where(AgentExecution.agent_name == agent_name)
            .order_by(AgentExecution.started_at.desc())
            .limit(limit)
        )
        if project_id:
            statement = statement.where(AgentExecution.project_id == project_id)
        return self.session.exec(statement).all()

    def get_running_executions(
        self,
        project_id: Optional[UUID] = None
    ) -> list[AgentExecution]:
        """Get all running executions.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            List of running executions
        """
        statement = select(AgentExecution).where(
            AgentExecution.status == AgentExecutionStatus.RUNNING
        )
        if project_id:
            statement = statement.where(AgentExecution.project_id == project_id)
        return self.session.exec(statement).all()

    def count_by_status(
        self,
        project_id: Optional[UUID] = None,
        agent_name: Optional[str] = None
    ) -> dict[str, int]:
        """Count executions by status.
        
        Args:
            project_id: Optional project filter
            agent_name: Optional agent filter
            
        Returns:
            Dictionary mapping status to count
        """
        statement = select(AgentExecution)
        if project_id:
            statement = statement.where(AgentExecution.project_id == project_id)
        if agent_name:
            statement = statement.where(AgentExecution.agent_name == agent_name)
        
        executions = self.session.exec(statement).all()
        
        counts = {
            "running": 0,
            "completed": 0,
            "failed": 0,
        }
        
        for execution in executions:
            if execution.status == AgentExecutionStatus.RUNNING:
                counts["running"] += 1
            elif execution.status == AgentExecutionStatus.COMPLETED:
                counts["completed"] += 1
            elif execution.status == AgentExecutionStatus.FAILED:
                counts["failed"] += 1
        
        return counts
