"""REST API endpoints for AI workflow management.

Provides endpoints to:
- Send messages to AI agents
- Approve/reject AI proposals
- Check agent execution status
- Trigger workflows (sprint planning, etc.)
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep
from app.agents.actions.database_actions import DatabaseActions
from app.crews import SprintPlanningFlow, StoryGenerationFlow
from app.kafka import (
    ApprovalResponseEvent,
    KafkaTopics,
    UserMessageEvent,
    get_kafka_producer,
)
from app.models import (
    AgentExecution,
    AgentExecutionStatus,
    ApprovalRequest,
    ApprovalStatus,
    Message as DBMessage,
    Project,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ==================== REQUEST/RESPONSE MODELS ====================


class ProcessMessageRequest(BaseModel):
    """Request to process a user message."""

    project_id: UUID
    content: str
    message_type: str = "text"


class ProcessMessageResponse(BaseModel):
    """Response from processing user message."""

    message_id: UUID
    execution_id: UUID
    status: str


class ApprovalDecisionRequest(BaseModel):
    """Request to approve or reject a proposal."""

    approved: bool
    feedback: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None


class ApprovalDecisionResponse(BaseModel):
    """Response from approval decision."""

    status: str
    approval_id: UUID
    message: str
    created_entity_id: Optional[UUID] = None


class ExecutionStatusResponse(BaseModel):
    """Agent execution status."""

    execution_id: UUID
    agent_name: str
    agent_type: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_ms: Optional[int]
    token_used: int
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]


class TriggerWorkflowRequest(BaseModel):
    """Request to trigger a workflow."""

    project_id: UUID
    workflow_type: str  # "story_generation", "sprint_planning"
    parameters: Dict[str, Any] = {}


class TriggerWorkflowResponse(BaseModel):
    """Response from workflow trigger."""

    flow_id: UUID
    workflow_type: str
    status: str
    message: str


# ==================== ENDPOINTS ====================


@router.post("/process-message", response_model=ProcessMessageResponse)
async def process_message(
    request: ProcessMessageRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Process a user message through AI agents.

    This triggers the story generation workflow which:
    1. Analyzes the message with TeamLeader
    2. Creates story proposal with BusinessAnalyst
    3. Sends approval request to user
    4. On approval, creates story in database
    """
    try:
        # Verify project access
        project = session.get(Project, request.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        if project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Save message to database
        message = DBMessage(
            project_id=request.project_id,
            author_type="USER",
            user_id=current_user.id,
            content=request.content,
            message_type=request.message_type,
        )
        session.add(message)
        session.commit()
        session.refresh(message)

        # Create agent execution record
        db_actions = DatabaseActions(session)
        execution = db_actions.create_agent_execution(
            project_id=request.project_id,
            agent_name="TeamLeader",
            agent_type="TeamLeader",
            trigger_message_id=message.id,
            user_id=current_user.id,
        )

        # Update execution to running
        db_actions.update_agent_execution(
            execution_id=execution.id,
            status=AgentExecutionStatus.RUNNING,
        )

        # Publish user message event to Kafka
        producer = await get_kafka_producer()
        await producer.publish(
            topic=KafkaTopics.USER_MESSAGES,
            event=UserMessageEvent(
                project_id=request.project_id,
                user_id=current_user.id,
                message_id=message.id,
                content=request.content,
                message_type=request.message_type,
            ),
        )

        # Trigger story generation flow
        flow = StoryGenerationFlow(
            db_session=session,
            project_id=request.project_id,
            user_id=current_user.id,
        )

        flow_result = await flow.run(
            user_message=request.content,
            execution_id=execution.id,
        )

        # Update execution based on flow result
        if flow_result.get("status") == "pending_approval":
            db_actions.update_agent_execution(
                execution_id=execution.id,
                status=AgentExecutionStatus.COMPLETED,
                result=flow_result,
            )
        else:
            db_actions.update_agent_execution(
                execution_id=execution.id,
                status=AgentExecutionStatus.FAILED,
                error_message=flow_result.get("error", "Unknown error"),
            )

        logger.info(f"Processed message {message.id} for project {request.project_id}")

        return ProcessMessageResponse(
            message_id=message.id,
            execution_id=execution.id,
            status="processing" if flow_result.get("status") == "pending_approval" else "failed",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post("/approve/{approval_id}", response_model=ApprovalDecisionResponse)
async def approve_proposal(
    approval_id: UUID,
    decision: ApprovalDecisionRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Approve or reject an AI agent's proposal."""
    try:
        # Get approval request
        approval = session.get(ApprovalRequest, approval_id)
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found",
            )

        # Verify project access
        project = session.get(Project, approval.project_id)
        if not project or project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )

        # Check if already processed
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval already {approval.status.value}",
            )

        db_actions = DatabaseActions(session)

        if decision.approved:
            # Approve
            db_actions.approve_request(
                approval_id=approval_id,
                user_id=current_user.id,
                user_feedback=decision.feedback,
                modified_data=decision.modified_data,
            )

            # Apply approval based on request type
            if approval.request_type == "story_creation":
                flow = StoryGenerationFlow(
                    db_session=session,
                    project_id=approval.project_id,
                    user_id=current_user.id,
                )
                result = await flow.apply_approval(
                    approval_id=approval_id,
                    user_feedback=decision.feedback,
                    modified_data=decision.modified_data,
                )

                # Publish approval response event
                producer = await get_kafka_producer()
                await producer.publish(
                    topic=KafkaTopics.APPROVAL_RESPONSES,
                    event=ApprovalResponseEvent(
                        project_id=approval.project_id,
                        user_id=current_user.id,
                        approval_request_id=approval_id,
                        approved=True,
                        feedback=decision.feedback,
                        modified_data=decision.modified_data,
                    ),
                )

                return ApprovalDecisionResponse(
                    status="approved_and_applied",
                    approval_id=approval_id,
                    message="Story created successfully",
                    created_entity_id=UUID(result.get("story_id")) if result.get("story_id") else None,
                )
            else:
                return ApprovalDecisionResponse(
                    status="approved",
                    approval_id=approval_id,
                    message="Proposal approved",
                )

        else:
            # Reject
            db_actions.reject_request(
                approval_id=approval_id,
                user_id=current_user.id,
                user_feedback=decision.feedback,
            )

            # Publish approval response event
            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.APPROVAL_RESPONSES,
                event=ApprovalResponseEvent(
                    project_id=approval.project_id,
                    user_id=current_user.id,
                    approval_request_id=approval_id,
                    approved=False,
                    feedback=decision.feedback,
                ),
            )

            return ApprovalDecisionResponse(
                status="rejected",
                approval_id=approval_id,
                message="Proposal rejected",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process approval decision: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process approval: {str(e)}",
        )


@router.get("/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Get agent execution status and details."""
    try:
        execution = session.get(AgentExecution, execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found",
            )

        # Verify access
        project = session.get(Project, execution.project_id)
        if not project or project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )

        return ExecutionStatusResponse(
            execution_id=execution.id,
            agent_name=execution.agent_name,
            agent_type=execution.agent_type,
            status=execution.status.value,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            duration_ms=execution.duration_ms,
            token_used=execution.token_used,
            error_message=execution.error_message,
            result=execution.result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )


@router.post("/trigger", response_model=TriggerWorkflowResponse)
async def trigger_workflow(
    request: TriggerWorkflowRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Trigger an AI workflow (sprint planning, etc.)."""
    try:
        # Verify project access
        project = session.get(Project, request.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        if project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )

        if request.workflow_type == "sprint_planning":
            flow = SprintPlanningFlow(
                db_session=session,
                project_id=request.project_id,
                user_id=current_user.id,
            )

            # Run sprint planning
            result = await flow.run(
                team_velocity=request.parameters.get("team_velocity", 40),
                sprint_duration=request.parameters.get("sprint_duration", 14),
                business_goals=request.parameters.get("business_goals"),
            )

            return TriggerWorkflowResponse(
                flow_id=UUID(result.get("flow_id", str(UUID()))),
                workflow_type=request.workflow_type,
                status=result.get("status", "unknown"),
                message=f"Sprint planning completed: {result.get('total_stories_analyzed', 0)} stories analyzed",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown workflow type: {request.workflow_type}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger workflow: {str(e)}",
        )


@router.get("/approvals/pending")
async def get_pending_approvals(
    project_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Get pending approval requests for a project."""
    try:
        # Verify access
        project = session.get(Project, project_id)
        if not project or project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )

        # Query pending approvals
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.project_id == project_id)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
            .order_by(ApprovalRequest.created_at.desc())
        )

        approvals = session.exec(stmt).all()

        return {
            "approvals": [
                {
                    "id": str(approval.id),
                    "request_type": approval.request_type,
                    "agent_name": approval.agent_name,
                    "proposed_data": approval.proposed_data,
                    "preview_data": approval.preview_data,
                    "explanation": approval.explanation,
                    "created_at": approval.created_at.isoformat(),
                }
                for approval in approvals
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pending approvals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approvals: {str(e)}",
        )
