"""Base Agent Class - Abstracts Kafka complexity from agent implementations.

This is the new simplified agent architecture where:
- Agents inherit from BaseAgent
- Implement handle_task() method
- Kafka consumer/producer logic is hidden
- Simple API: message_user() for all communications
"""

import asyncio
import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from app.kafka.producer import KafkaProducer, get_kafka_producer
from app.kafka.event_schemas import (
    AgentEvent,
    AgentResponseEvent,
    AgentTaskType,
    DelegationRequestEvent,
    KafkaTopics,
    RouterTaskEvent,
)
from app.models import Agent as AgentModel, AgentStatus
from datetime import datetime, timezone
from app.core.langfuse_client import (
    get_langfuse_client,
    get_langfuse_context,
    flush_langfuse, 
    create_session_id,
    score_current,
    update_current_trace,
    update_current_observation,
    format_llm_usage,
    format_chat_messages,
    get_langchain_callback,
)

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """Simplified task context for agent consumption."""

    task_id: UUID
    task_type: AgentTaskType
    priority: str
    routing_reason: str
    message_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    content: str = ""
    message_type: str = "text"
    execution_mode: str = "interactive"  # NEW: "interactive" | "background" | "silent"
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass
class TaskResult:
    success: bool
    output: str  
    structured_data: Optional[Dict[str, Any]] = None  
    requires_approval: bool = False  
    error_message: Optional[str] = None


# Cross-agent collaboration exceptions
class CollaborationError(Exception):
    """Base exception for collaboration failures."""
    pass


class CollaborationTimeoutError(CollaborationError):
    """Raised when collaboration request times out."""
    pass


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Architecture:
    - Kafka consumer/producer logic hidden from subclasses
    - Agents only implement handle_task()
    - Helpers for progress tracking and publishing
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize base agent with persona attributes.
        """
        self.agent_id = agent_model.id
        self.project_id = agent_model.project_id
        self.role_type = agent_model.role_type
        self.agent_model = agent_model
        
        # Name (short and display)
        self.name = agent_model.human_name  # "Sarah"
        self.display_name = agent_model.name  # "Sarah (Business Analyst)"
        
        # Persona attributes (simplified - easy access for subclasses)
        self.persona_template_id = agent_model.persona_template_id
        self.personality_traits = agent_model.personality_traits or []
        self.communication_style = agent_model.communication_style
        self.persona_metadata = agent_model.persona_metadata or {}

        # For AgentPool compatibility
        self.heartbeat_interval = kwargs.get("heartbeat_interval", 30)
        self.max_idle_time = kwargs.get("max_idle_time", 300)

        # Agent state and statistics
        self.state = AgentStatus.idle  # Current agent state
        self.total_executions = 0  # Total tasks completed
        self.successful_executions = 0  # Successful tasks
        self.failed_executions = 0  # Failed tasks

        # Callbacks (for AgentPool compatibility)
        self.on_state_change = None
        self.on_execution_complete = None
        self.on_heartbeat = None

        # Current task being processed (for progress tracking)
        self._current_task_id: Optional[UUID] = None
        self._current_execution_id: Optional[UUID] = None
        
        # Task context tracking (for clarification questions)
        self._current_task_type: Optional[str] = None
        self._current_task_content: Optional[str] = None
        self._current_routing_reason: Optional[str] = None
        self._current_user_id: Optional[UUID] = None
        self._current_execution_mode: str = "interactive"  # NEW: Track execution mode
        
        # Execution tracking
        self._execution_start_time: Optional[Any] = None  # datetime object
        self._execution_events: list = []  # List of events for current execution

        # Kafka producer (lazy init)
        self._producer: Optional[KafkaProducer] = None

        # Consumer will be created by start()
        self._consumer = None

        # Task queue for sequential processing
        self._task_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._queue_running: bool = False
        self._queue_worker_task: Optional[asyncio.Task] = None

        # Langfuse tracing
        self.langfuse_client = get_langfuse_client()
        self._current_trace_id: Optional[str] = None
        self._current_trace: Optional[Any] = None  # Current Langfuse trace object

        # Cross-agent collaboration
        self._pending_collaborations: Dict[UUID, asyncio.Future] = {}

        logger.info(
            f"Initialized {self.role_type} agent: {self.name} "
            f"(style: {self.communication_style or 'N/A'}, traits: {', '.join(self.personality_traits[:2]) if self.personality_traits else 'N/A'})"
        )

    @abstractmethod
    async def handle_task(self, task: TaskContext) -> TaskResult:
      
        """Handle assigned task.

        This is the ONLY method agents need to implement.

        Args:
            task: TaskContext with task details

        Returns:
            TaskResult with output and success status

        Example:
            async def handle_task(self, task: TaskContext) -> TaskResult:
                await self.message_user("progress", "Processing...", {"step": 1, "total": 2})
                result = await self._process(task.content)
                await self.message_user("progress", "Complete", {"step": 2, "total": 2})
                
                return TaskResult(
                    success=True,
                    output=result,
                    structured_data={"key": "value"}
                )
        """
        pass

    async def message_user(
        self,
        event_type: str,
        content: str,
        details: Optional[Dict[str, Any]] = None,
        *,
        artifact_config: Optional[Dict[str, Any]] = None,
        question_config: Optional[Dict[str, Any]] = None,
        display_mode: Optional[str] = None,  # NEW: "chat" | "progress_bar" | "notification" | "none"
        save_to_db: bool = True,
        broadcast_ws: bool = True,
        **kwargs
    ) -> Optional[UUID]:
        """Send message/event to user with support for artifacts and questions.
        
        This is the unified messaging API for all agent-to-user communication:
        - Simple messages/events (thinking, progress, response)
        - Clarification questions (with DB persistence and pause handling)
        - Artifacts (with DB persistence and file storage)
        
        Args:
            event_type: Event type - determines behavior:
                - "thinking", "tool_call", "progress", "response": Simple events
                - "artifact": Creates artifact with persistence
                - "question": Asks clarification question with pause
                - "completed": Marks task complete
            content: Message content (human-readable text)
            details: Additional structured data for event payload
            artifact_config: Configuration for artifact creation (when event_type="artifact")
            question_config: Configuration for questions (when event_type="question")
            save_to_db: Whether to persist to messages table (default: True)
            broadcast_ws: Whether to broadcast to WebSocket (default: True)
            **kwargs: Extra metadata
        
        Returns:
            UUID: For artifacts/questions, returns the created ID
            None: For simple messages
        
        Examples:
            # Simple message
            await self.message_user("response", "Analysis complete")
            
            # Create artifact
            artifact_id = await self.message_user(
                "artifact",
                "Created PRD for login feature",
                artifact_config={
                    "artifact_type": "prd",
                    "title": "Login Feature PRD",
                    "content": prd_data,
                    "description": "Comprehensive requirements",
                    "tags": ["prd", "login"]
                }
            )
            
            # Ask question
            question_id = await self.message_user(
                "question",
                "Which authentication method?",
                question_config={
                    "question_type": "multichoice",
                    "options": ["OAuth", "JWT", "Session"],
                    "allow_multiple": False
                }
            )
        """
        if not self._current_task_id:
            logger.warning(f"[{self.name}] Cannot send message: no active task")
            return None

        try:
            # Handle artifact creation
            if event_type == "artifact":
                return await self._handle_artifact_message(content, artifact_config, details, **kwargs)
            
            # Handle clarification questions
            if event_type == "question":
                return await self._handle_question_message(content, question_config, details, **kwargs)
            
            # Handle simple messages/events
            return await self._handle_simple_message(event_type, content, details, display_mode, save_to_db, broadcast_ws, **kwargs)

        except Exception as e:
            logger.error(f"[{self.name}] Failed to send message: {e}", exc_info=True)
            return None
    
    async def _handle_simple_message(
        self,
        event_type: str,
        content: str,
        details: Optional[Dict[str, Any]],
        display_mode: Optional[str],
        save_to_db: bool,
        broadcast_ws: bool,
        **kwargs
    ) -> None:
        """Handle simple message/event with execution context."""
        producer = await self._get_producer()
        
        # Determine display mode (smart defaults)
        if display_mode is None:
            display_mode = self._get_default_display_mode(event_type)
        
        # Save to DB first for response/completed events (single source of truth)
        message_id = None
        if save_to_db and event_type in ["response", "completed"]:
            message_type = (details or {}).get("message_type", "text")
            message_id = await self._save_message_to_db(content, message_type, details, **kwargs)
        
        event = AgentEvent(
            event_type=f"agent.{event_type}",
            agent_name=self.name,
            agent_id=str(self.agent_id),
            project_id=str(self.project_id) if self.project_id else None,
            execution_id=str(self._current_execution_id) if self._current_execution_id else None,
            task_id=str(self._current_task_id) if self._current_task_id else None,
            content=content,
            details={
                **(details or {}),
                "message_id": str(message_id) if message_id else None,  # Include DB message_id
            },
            execution_context={
                "mode": self._current_execution_mode,
                "task_id": str(self._current_task_id) if self._current_task_id else None,
                "task_type": self._current_task_type or "unknown",
                "display_mode": display_mode,
            },
            metadata={
                "agent_type": self.role_type,
                "agent_execution_id": str(self._current_execution_id) if self._current_execution_id else None,
                **kwargs
            }
        )
        
        await producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=event)
        
        logger.info(f"[{self.name}] {event_type}: {content[:100]}")
    
    def _get_default_display_mode(self, event_type: str) -> str:
        """Determine default display mode based on execution mode and event type.
        
        Returns:
            "chat" | "progress_bar" | "notification" | "none"
        """
        mode = self._current_execution_mode
        
        if mode == "interactive":
            # Interactive: All events go to chat
            return "chat"
        
        elif mode == "background":
            # Background: Different display per event type
            if event_type == "thinking":
                return "none"  # Skip thinking events
            elif event_type == "progress":
                return "progress_bar"  # Show in progress panel
            elif event_type in ["response", "completed"]:
                return "notification"  # Show as toast
            else:
                return "none"  # Default: skip
        
        else:  # silent
            # Silent: Only log, no UI
            return "none"
    
    async def _handle_artifact_message(
        self,
        content: str,
        artifact_config: Optional[Dict[str, Any]],
        details: Optional[Dict[str, Any]],
        **kwargs
    ) -> UUID:
        """Handle artifact creation message."""
        if not artifact_config:
            raise ValueError("artifact_config required for event_type='artifact'")
        
        from app.services.artifact_service import ArtifactService
        from app.models import ArtifactType
        from sqlmodel import Session
        from app.core.db import engine
        
        # Extract config
        artifact_type = artifact_config.get("artifact_type")
        title = artifact_config.get("title", "Untitled Artifact")
        artifact_content = artifact_config.get("content", {})
        description = artifact_config.get("description")
        tags = artifact_config.get("tags", [])
        save_to_file = artifact_config.get("save_to_file", True)
        
        # Validate artifact type
        try:
            artifact_type_enum = ArtifactType(artifact_type)
        except ValueError:
            raise ValueError(
                f"Invalid artifact type: {artifact_type}. "
                f"Valid types: {[t.value for t in ArtifactType]}"
            )
        
        # Create artifact
        with Session(engine) as session:
            service = ArtifactService(session)
            artifact = service.create_artifact(
                project_id=self.project_id,
                agent_id=self.agent_id,
                agent_name=self.name,
                artifact_type=artifact_type_enum,
                title=title,
                content=artifact_content,
                description=description,
                save_to_file=save_to_file,
                tags=tags
            )
            
            artifact_id = artifact.id
            
            logger.info(
                f"[{self.name}] Created artifact: {artifact.artifact_type.value} "
                f"'{title}' (id={artifact_id}, version={artifact.version})"
            )
        
        # Send agent event with artifact info
        await self._handle_simple_message(
            "response",
            content,
            {
                **(details or {}),
                "message_type": "artifact_created",
                "artifact_id": str(artifact_id),
                "artifact_type": artifact_type,
                "artifact_title": title,
            },
            display_mode=None,  # Use default display mode
            save_to_db=True,
            broadcast_ws=False,
            **kwargs
        )
        
        # Broadcast artifact creation to WebSocket
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project(
            {
                "type": "artifact_created",
                "artifact_id": str(artifact_id),
                "artifact_type": artifact_type,
                "title": title,
                "description": description,
                "agent_name": self.name,
                "version": artifact.version,
                "status": artifact.status.value,
                "file_path": artifact.file_path,
                "tags": tags,
                "timestamp": artifact.created_at.isoformat()
            },
            self.project_id
        )
        
        return artifact_id
    
    async def _handle_question_message(
        self,
        content: str,
        question_config: Optional[Dict[str, Any]],
        details: Optional[Dict[str, Any]],
        **kwargs
    ) -> UUID:
        """Handle clarification question message."""
        if not question_config:
            raise ValueError("question_config required for event_type='question'")
        
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import AgentQuestion, QuestionType, QuestionStatus, Message, AuthorType
        from app.kafka.event_schemas import QuestionAskedEvent
        from datetime import timedelta
        
        # Extract config
        question_type = question_config.get("question_type", "open")
        options = question_config.get("options")
        allow_multiple = question_config.get("allow_multiple", False)
        proposed_data = question_config.get("proposed_data")
        explanation = question_config.get("explanation")
        custom_context = question_config.get("context", {})  # Custom context from caller
        
        question_id = uuid4()
        
        # Get current task context
        task_context_data = {
            "task_id": str(self._current_task_id),
            "task_type": self._current_task_type,
            "execution_id": str(self._current_execution_id) if self._current_execution_id else None,
            "original_message": self._current_task_content,
            "routing_reason": self._current_routing_reason,
            "question_context": custom_context,  # Include custom context for resume
        }
        
        # Save to database (dual storage: agent_questions + messages)
        with Session(engine) as session:
            # 1. Save to agent_questions table (for workflow)
            db_question = AgentQuestion(
                id=question_id,
                project_id=self.project_id,
                agent_id=self.agent_id,
                user_id=self._current_user_id,
                question_type=QuestionType(question_type),
                question_text=content,
                options=options,
                allow_multiple=allow_multiple,
                proposed_data=proposed_data,
                explanation=explanation,
                status=QuestionStatus.WAITING_ANSWER,
                task_id=self._current_task_id,
                execution_id=self._current_execution_id,
                task_context=task_context_data,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            session.add(db_question)
            
            # 2. Also save to messages table (for chat history)
            question_message = Message(
                id=question_id,
                project_id=self.project_id,
                author_type=AuthorType.AGENT,
                agent_id=self.agent_id,
                content=content,
                message_type="agent_question",
                structured_data={
                    "question_id": str(question_id),
                    "question_type": question_type,
                    "options": options,
                    "allow_multiple": allow_multiple,
                    "status": "waiting_answer"
                },
                message_metadata={
                    "agent_name": self.name,
                    "task_id": str(self._current_task_id),
                    "execution_id": str(self._current_execution_id) if self._current_execution_id else None,
                }
            )
            session.add(question_message)
            session.commit()
        
        # Publish event to Kafka
        producer = await self._get_producer()
        event = QuestionAskedEvent(
            question_id=str(question_id),
            agent_id=str(self.agent_id),
            agent_name=self.name,
            project_id=str(self.project_id) if self.project_id else None,
            user_id=str(self._current_user_id) if self._current_user_id else None,
            question_type=question_type,
            question_text=content,
            options=options,
            allow_multiple=allow_multiple,
            proposed_data=proposed_data,
            explanation=explanation,
            task_id=str(self._current_task_id),
            execution_id=str(self._current_execution_id) if self._current_execution_id else None,
        )
        
        await producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=event)
        
        # Broadcast to WebSocket
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.question",
                "question_id": str(question_id),
                "agent_name": self.name,
                "question": content,
                "question_type": question_type,
                "options": options,
                "allow_multiple": allow_multiple,
                "proposed_data": proposed_data,
                "explanation": explanation,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            self.project_id
        )
        
        logger.info(f"[{self.name}] Asked question (id={question_id}): {content[:100]}")
        
        return question_id
    
    async def _save_message_to_db(
        self,
        content: str,
        message_type: str,
        structured_data: Optional[Dict[str, Any]] = None,
        **metadata
    ) -> UUID:
        """Save message to messages table for persistence.
        
        Returns:
            UUID: The message ID that was created
        """
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Message, AuthorType
        
        message_id = uuid4()
        
        with Session(engine) as session:
            message = Message(
                id=message_id,
                project_id=self.project_id,
                author_type=AuthorType.AGENT,
                agent_id=self.agent_id,
                content=content,
                message_type=message_type,
                structured_data=structured_data or {},
                message_metadata={
                    "agent_name": self.name,
                    "task_id": str(self._current_task_id),
                    "execution_id": str(self._current_execution_id) if self._current_execution_id else None,
                    **metadata
                }
            )
            session.add(message)
            session.commit()
        
        return message_id
    
    async def start_execution(self) -> None:
        """Emit: agent.messaging.start - Notify that agent began execution"""
        await self.message_user("thinking", f"{self.name} is starting...")
    
    async def emit_tool(self, tool: str, action: str, state: str = "started", **details) -> None:
        """Emit: agent.messaging.tool_call - Track tool execution
        
        Args:
            tool: Tool name (e.g., "read_file", "web_search")
            action: Human-readable action (e.g., "Reading main.py")
            state: "started", "completed", or "failed"
            **details: Additional tool details (input, output, error)
        """
        await self.message_user("tool_call", action, {"tool": tool, "state": state, **details})
    
    async def emit_message(self, content: str, message_type: str = "text", data: Any = None) -> None:
        """Emit: agent.messaging.response - Send agent message (saves to DB)
        
        Args:
            content: Message content
            message_type: "text", "prd", "backlog", "code", etc.
            data: Structured data for rich messages
        """
        await self.message_user("response", content, {"message_type": message_type, "data": data})
    
    async def finish_execution(self, summary: str = "Task completed") -> None:
        """Emit: agent.messaging.finish - Notify execution is complete"""

        await self.message_user("completed", summary)
    
    async def ask_clarification_question(
        self,
        question: str,
        question_type: str = "open",
        options: Optional[list[str]] = None,
        allow_multiple: bool = False,
    ) -> UUID:
        """DEPRECATED: Use message_user(event_type="question") instead.
        
        This method is kept for backward compatibility and will delegate
        to the unified message_user() API.
        
        Args:
            question: Question text to ask user
            question_type: "open" or "multichoice"
            options: List of options for multichoice
            allow_multiple: Allow multiple selections (multichoice only)
            
        Returns:
            question_id: UUID of created question
        """
        logger.warning(
            f"[{self.name}] ask_clarification_question() is deprecated. "
            "Use message_user(event_type='question') instead."
        )
        
        return await self.message_user(
            "question",
            question,
            question_config={
                "question_type": question_type,
                "options": options,
                "allow_multiple": allow_multiple
            }
        )

    async def ask_approval(
        self,
        proposal_title: str,
        proposed_data: Dict[str, Any],
        explanation: Optional[str] = None,
        allow_modification: bool = True
    ) -> Dict[str, Any]:
        """Ask user to approve/reject a proposal.
        
        Agent execution will pause until user responds.
        
        Args:
            proposal_title: Title of the proposal (e.g., "Create PRD Document")
            proposed_data: The data being proposed (e.g., PRD content)
            explanation: Why this approval is needed
            allow_modification: Whether user can modify the data
        
        Returns:
            {
                "approved": bool,
                "feedback": str | None,
                "modified_data": dict | None,
                "final_data": dict  # proposed_data or modified_data
            }
        
        Example:
            >>> result = await self.ask_approval(
            ...     proposal_title="Create User Stories",
            ...     proposed_data={"stories": [...], "acceptance_criteria": [...]},
            ...     explanation="Based on the PRD analysis"
            ... )
            >>> if result["approved"]:
            ...     await self.create_stories(result["final_data"])
        """
        question_id = await self.message_user(
            "question",
            proposal_title,
            question_config={
                "question_type": "approval",
                "proposed_data": proposed_data,
                "explanation": explanation,
                "allow_modification": allow_modification,
            }
        )
        
        # Wait for user answer (blocking)
        # The answer will be provided by QuestionAnswerRouter via RESUME task
        # For now, return question_id - the calling code should handle the pause/resume
        logger.info(f"[{self.name}] Waiting for approval (question_id={question_id})")
        
        # Return placeholder - actual implementation will need CrewAI Flow pause/resume
        return {
            "question_id": str(question_id),
            "status": "waiting_approval"
        }

    async def ask_multiple_clarification_questions(
        self,
        questions: list[dict]
    ) -> list[UUID]:
        """Tool: Ask multiple clarification questions at once (batch mode).
        
        This method will:
        1. Save all questions to DB (agent_questions + messages tables)
        2. Publish BatchQuestionsAskedEvent to broadcast to frontend
        3. Return list of question_ids for tracking
        
        The current task will be PAUSED until user answers ALL questions.
        When user answers all, router will resume the task with all answers.
        
        Args:
            questions: List of question dicts, each with:
                - question_text: str
                - question_type: "open" | "multichoice"
                - options: list[str] (optional)
                - allow_multiple: bool (optional)
                - context: str (optional, e.g., "domain", "user_roles", "priority")
        
        Returns:
            List of question IDs (UUIDs)
            
        Example:
            question_ids = await self.ask_multiple_clarification_questions([
                {
                    "question_text": "Loại website nào?",
                    "question_type": "multichoice",
                    "options": ["Type A", "Type B", "Other"],
                    "allow_multiple": False,
                    "context": "domain"
                },
                {
                    "question_text": "Người dùng nào?",
                    "question_type": "multichoice",
                    "options": ["User A", "User B", "Other"],
                    "allow_multiple": True,
                    "context": "user_roles"
                }
            ])
        """
        if not self._current_task_id:
            raise RuntimeError("Cannot ask questions: no active task")
        
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import AgentQuestion, Message, AuthorType, QuestionType, QuestionStatus
        from datetime import timedelta
        
        question_ids = []
        batch_id = str(uuid4())  # Unique batch ID
        
        # Get current task context
        task_context_data = {
            "task_id": str(self._current_task_id),
            "task_type": self._current_task_type,
            "execution_id": str(self._current_execution_id) if self._current_execution_id else None,
            "original_message": self._current_task_content,
            "routing_reason": self._current_routing_reason,
        }
        
        # Save all questions to database
        batch_message_id = uuid4()  # Single message ID for the entire batch
        
        with Session(engine) as session:
            # 1. Save individual AgentQuestion records (for workflow tracking)
            for idx, q_data in enumerate(questions):
                question_id = uuid4()
                question_ids.append(question_id)
                
                db_question = AgentQuestion(
                    id=question_id,
                    project_id=self.project_id,
                    agent_id=self.agent_id,
                    user_id=self._current_user_id,
                    question_type=QuestionType(q_data["question_type"]),
                    question_text=q_data["question_text"],
                    options=q_data.get("options"),
                    allow_multiple=q_data.get("allow_multiple", False),
                    status=QuestionStatus.WAITING_ANSWER,
                    task_id=self._current_task_id,
                    execution_id=self._current_execution_id,
                    task_context={
                        **task_context_data,
                        "batch_id": batch_id,
                        "batch_index": idx,
                        "batch_total": len(questions),
                        "question_context": q_data.get("context"),
                    },
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                )
                session.add(db_question)
            
            # 2. Save ONE combined message for chat history (not per-question)
            # Build questions array for structured_data
            combined_questions = [
                {
                    "question_id": str(question_ids[idx]),
                    "question_text": q_data["question_text"],
                    "question_type": q_data["question_type"],
                    "options": q_data.get("options"),
                    "allow_multiple": q_data.get("allow_multiple", False),
                    "context": q_data.get("context"),
                }
                for idx, q_data in enumerate(questions)
            ]
            
            batch_message = Message(
                id=batch_message_id,
                project_id=self.project_id,
                author_type=AuthorType.AGENT,
                agent_id=self.agent_id,
                content=f"Batch of {len(questions)} questions",  # Summary text
                message_type="agent_question_batch",
                structured_data={
                    "batch_id": batch_id,
                    "questions": combined_questions,
                    "question_ids": [str(qid) for qid in question_ids],
                    "status": "waiting_answer",
                    "answered": False,
                },
                message_metadata={
                    "agent_name": self.name,
                    "task_id": str(self._current_task_id),
                    "execution_id": str(self._current_execution_id) if self._current_execution_id else None,
                }
            )
            session.add(batch_message)
            
            session.commit()
        
        # Publish batch event to Kafka (will add event schema next)
        producer = await self._get_producer()
        
        # Import will be added after we create the event schema
        from app.kafka.event_schemas import BatchQuestionsAskedEvent
        
        event = BatchQuestionsAskedEvent(
            batch_id=batch_id,
            question_ids=[str(qid) for qid in question_ids],
            questions=questions,
            agent_id=str(self.agent_id),
            agent_name=self.name,
            project_id=str(self.project_id) if self.project_id else None,
            user_id=str(self._current_user_id) if self._current_user_id else None,
            task_id=str(self._current_task_id),
            execution_id=str(self._current_execution_id) if self._current_execution_id else None,
        )
        
        await producer.publish(
            topic=KafkaTopics.AGENT_EVENTS,
            event=event
        )
        
        # Broadcast to WebSocket
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.question_batch",
                "batch_id": batch_id,
                "question_ids": [str(qid) for qid in question_ids],
                "questions": questions,
                "agent_name": self.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            self.project_id
        )
        
        logger.info(f"[{self.name}] Asked {len(questions)} questions in batch (batch_id={batch_id})")
        
        return question_ids

    async def create_artifact(
        self,
        artifact_type: str,
        title: str,
        content: dict,
        description: str = None,
        save_to_file: bool = True,
        tags: List[str] = None
    ) -> UUID:
        """DEPRECATED: Use message_user(event_type="artifact") instead.
        
        This method is kept for backward compatibility and will delegate
        to the unified message_user() API.
        
        Args:
            artifact_type: Type of artifact (prd, architecture, code, test_plan, etc.)
            title: Human-readable title
            content: Structured content dict
            description: Optional description
            save_to_file: Whether to save to file system (default: True)
            tags: Optional tags for categorization
        
        Returns:
            Artifact ID
        """
        logger.warning(
            f"[{self.name}] create_artifact() is deprecated. "
            "Use message_user(event_type='artifact') instead."
        )
        
        return await self.message_user(
            "artifact",
            f"Created {artifact_type}: {title}",
            artifact_config={
                "artifact_type": artifact_type,
                "title": title,
                "content": content,
                "description": description,
                "save_to_file": save_to_file,
                "tags": tags or []
            }
        )

    async def _broadcast_artifact(self, artifact):
        """Broadcast artifact creation to WebSocket clients.
        
        Args:
            artifact: Artifact instance to broadcast
        """
        from app.websocket.connection_manager import connection_manager
        
        await connection_manager.broadcast_to_project(
            {
                "type": "artifact_created",
                "artifact_id": str(artifact.id),
                "artifact_type": artifact.artifact_type.value,
                "title": artifact.title,
                "description": artifact.description,
                "agent_name": artifact.agent_name,
                "version": artifact.version,
                "status": artifact.status.value,
                "file_path": artifact.file_path,
                "tags": artifact.tags,
                "timestamp": artifact.created_at.isoformat()
            },
            self.project_id
        )

    async def delegate_to_role(
        self,
        task: "TaskContext",
        target_role: str,
        delegation_message: str,
        priority: str = "high"
    ) -> "TaskResult":
        """Delegate task to an agent by role (Router will select specific agent).
        
        This is the simplified delegation API - agents just specify the target role,
        and Router handles finding the best available agent, updating context, etc.
        
        Args:
            task: Original task context to delegate
            target_role: Target agent role (business_analyst, developer, tester, architect)
            delegation_message: Message to show user about delegation
            priority: Task priority (default: "high")
            
        Returns:
            TaskResult indicating delegation initiated
            
        Example:
            # Delegate to Business Analyst
            return await self.delegate_to_role(
                task=task,
                target_role="business_analyst",
                delegation_message="Tôi đã chuyển cho @BusinessAnalyst để phân tích! 📊"
            )
        """
        try:
            producer = await self._get_producer()
            
            # Publish delegation request - Router will handle agent selection
            delegation_event = DelegationRequestEvent(
                event_type="delegation.request",
                project_id=str(self.project_id) if self.project_id else None,
                user_id=str(task.user_id) if task.user_id else None,
                original_task_id=str(task.task_id),
                delegating_agent_id=str(self.agent_id),
                delegating_agent_name=self.name,
                target_role=target_role,
                priority=priority,
                task_type=AgentTaskType.MESSAGE,
                content=task.content,
                context=task.context,
                delegation_message=delegation_message,
                source_event_type=task.context.get("source_event_type", "user.message.sent"),
                source_event_id=task.context.get("source_event_id", str(task.task_id)),
            )
            
            await producer.publish(
                topic=KafkaTopics.DELEGATION_REQUESTS,
                event=delegation_event
            )
                        
            return TaskResult(
                success=True,
                output="",  # Empty output - message already sent above
                structured_data={
                    "delegation_to_role": target_role,
                    "delegation_status": "pending"
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Error delegating to role {target_role}: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Failed to delegate: {str(e)}"
            )

    # =========================================================================
    # CROSS-AGENT COLLABORATION
    # =========================================================================

    async def ask_specialist(
        self,
        target_role: str,
        question: str,
        request_type: str = "clarification",
        context: Dict[str, Any] = None,
        timeout: int = 300,
    ) -> str:
        """Ask another specialist agent directly for collaboration.
        
        This enables direct agent-to-agent communication for:
        - Clarification requests (Dev → BA)
        - Review requests (Tester → Dev)  
        - Estimation requests (BA → Dev)
        - Validation requests (any → any)
        
        Args:
            target_role: Target agent role ("business_analyst", "developer", "tester")
            question: The question or request to send
            request_type: Type of request ("clarification", "review", "estimation", "validation")
            context: Additional context (story_id, code_snippet, etc.)
            timeout: Max wait time in seconds (default: 300 = 5 min)
            
        Returns:
            Response string from the target agent
            
        Raises:
            CollaborationTimeoutError: If target doesn't respond in time
            CollaborationError: If collaboration fails
            
        Example:
            # Developer asking BA for clarification
            answer = await self.ask_specialist(
                target_role="business_analyst",
                question="What's the expected behavior for login failure?",
                request_type="clarification",
                context={"story_id": "123"}
            )
        """
        from app.kafka.event_schemas import AgentCollaborationRequest
        
        request_id = uuid4()
        
        # Create future to wait for response
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_collaborations[request_id] = future
        
        try:
            producer = await self._get_producer()
            
            # Build collaboration request
            request = AgentCollaborationRequest(
                request_id=request_id,
                from_agent_id=self.agent_id,
                from_agent_role=self.role_type,
                to_agent_role=target_role,
                request_type=request_type,
                question=question,
                context={
                    "task_id": str(self._current_task_id) if self._current_task_id else None,
                    "project_id": str(self.project_id),
                    **(context or {})
                },
                project_id=str(self.project_id),
                user_id=str(self._current_user_id) if self._current_user_id else None,
            )
            
            # Publish request
            await producer.publish(
                topic=KafkaTopics.AGENT_COLLABORATION,
                event=request
            )
            
            logger.info(
                f"[{self.name}] Sent collaboration request to {target_role}: "
                f"{question[:50]}..."
            )
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            
            logger.info(f"[{self.name}] Received collaboration response from {target_role}")
            return response
            
        except asyncio.TimeoutError:
            # Clean up pending collaboration
            self._pending_collaborations.pop(request_id, None)
            error_msg = f"No response from {target_role} after {timeout}s"
            logger.warning(f"[{self.name}] Collaboration timeout: {error_msg}")
            raise CollaborationTimeoutError(error_msg)
            
        except Exception as e:
            self._pending_collaborations.pop(request_id, None)
            logger.error(f"[{self.name}] Collaboration error: {e}", exc_info=True)
            raise CollaborationError(f"Collaboration failed: {str(e)}")

    async def handle_collaboration_request(
        self,
        request_id: UUID,
        question: str,
        request_type: str,
        from_agent_role: str,
        context: Dict[str, Any]
    ) -> str:
        """Handle incoming collaboration request from another agent.
        
        Override this method in subclasses to provide custom handling.
        Default implementation uses LLM to generate a response based on the agent's expertise.
        
        Args:
            request_id: Unique request identifier
            question: The question being asked
            request_type: Type of request (clarification, review, estimation, validation)
            from_agent_role: Role of the requesting agent
            context: Additional context provided
            
        Returns:
            Response string to send back
        """
        # Default implementation - subclasses can override for custom behavior
        logger.info(
            f"[{self.name}] Handling collaboration request from {from_agent_role}: "
            f"{question[:50]}..."
        )
        
        # Generate response based on agent's expertise
        prompt = f"""You are a {self.role_type} agent. Another agent ({from_agent_role}) is asking for {request_type}:

Question: {question}

Context: {context}

Provide a helpful, concise response based on your expertise as a {self.role_type}.
"""
        
        # Use LLM to generate response (if available)
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"[{self.name}] Failed to generate collaboration response: {e}")
            return f"I apologize, I couldn't process your {request_type} request at this time."

    async def _send_collaboration_response(
        self,
        request_id: str,
        to_agent_id: str,
        response: str,
        success: bool = True,
        error: str = None
    ) -> None:
        """Send response to a collaboration request."""
        from app.kafka.event_schemas import AgentCollaborationResponse
        
        producer = await self._get_producer()
        
        response_event = AgentCollaborationResponse(
            request_id=UUID(request_id) if isinstance(request_id, str) else request_id,
            from_agent_id=self.agent_id,
            to_agent_id=UUID(to_agent_id) if isinstance(to_agent_id, str) else to_agent_id,
            response=response,
            success=success,
            error=error,
            project_id=str(self.project_id),
        )
        
        await producer.publish(
            topic=KafkaTopics.AGENT_COLLABORATION,
            event=response_event
        )
        
        logger.info(f"[{self.name}] Sent collaboration response for request {request_id}")

    async def _handle_collaboration_response(
        self,
        request_id: UUID,
        response: str,
        success: bool,
        error: str = None
    ) -> None:
        """Handle incoming collaboration response (resume waiting agent)."""
        future = self._pending_collaborations.pop(request_id, None)
        
        if future is None:
            logger.warning(
                f"[{self.name}] Received response for unknown request {request_id}"
            )
            return
        
        if future.done():
            logger.warning(
                f"[{self.name}] Future for request {request_id} already completed"
            )
            return
        
        if success:
            future.set_result(response)
        else:
            future.set_exception(CollaborationError(error or "Collaboration failed"))

    def get_langfuse_callback(
        self,
        trace_name: str,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[Any]:
        """Get Langfuse callback handler for LangChain integration (v3 API).
        
        Usage:
            callback = self.get_langfuse_callback("my_llm_call")
            response = await llm.ainvoke(messages, config={"callbacks": [callback]} if callback else {})
        """
        return get_langchain_callback(
            trace_name=trace_name,
            user_id=str(self._current_user_id) if self._current_user_id else None,
            session_id=str(self.project_id),
            tags=tags or [self.role_type],
            metadata={
                "agent_id": str(self.agent_id),
                "agent_name": self.name,
                "agent_role": self.role_type,
                "task_id": str(self._current_task_id) if self._current_task_id else None,
                **(metadata or {})
            }
        )

    def track_llm_generation(
        self,
        name: str,
        model: str,
        input_messages: List[Any],
        response: Any,
        model_parameters: Dict[str, Any] = None,
        duration_ms: float = None,
    ) -> bool:
        """Track LLM generation with timing.
        
        Args:
            name: Generation name (e.g., "routing_decision")
            model: Model name (e.g., "gpt-4o-mini")
            input_messages: List of input messages
            response: LLM response object
            model_parameters: Optional model params
            duration_ms: Execution time in milliseconds (measure around ainvoke call)
        
        Usage:
            start = time.time()
            response = await llm.ainvoke(messages)
            duration_ms = (time.time() - start) * 1000
            
            agent.track_llm_generation(
                name="routing",
                model="gpt-4o-mini", 
                input_messages=messages,
                response=response,
                duration_ms=duration_ms
            )
        
        Returns:
            True if tracked successfully
        """

        
        try:
            # Extract output content
            output_content = ""
            if hasattr(response, "content"):
                output_content = response.content
            elif isinstance(response, dict) and "content" in response:
                output_content = response["content"]
            elif isinstance(response, str):
                output_content = response
            
            # Extract token usage
            usage = format_llm_usage(response)
            
            # Build metadata
            metadata = {
                "name": name,
                "model": model,
                "model_parameters": model_parameters or {},
                "input": format_chat_messages(input_messages),
                "usage": usage,
                "agent": self.name,
                "agent_role": self.role_type
            }
            
            # Add duration if provided
            if duration_ms is not None:
                metadata["duration_ms"] = round(duration_ms, 2)
                metadata["latency_ms"] = round(duration_ms, 2)  # Alias for Langfuse
            
            # Update current observation if inside @observe
            updated = update_current_observation(
                output=output_content,
                metadata=metadata
            )
            
            if updated:
                logger.debug(f"[{self.name}] LLM tracked: {name}, model={model}, duration={duration_ms:.0f}ms" if duration_ms else f"[{self.name}] LLM tracked: {name}, model={model}")
            return updated
            
        except Exception as e:
            logger.debug(f"[{self.name}] track_llm_generation: {e}")
            return False

    def create_span(
        self,
        name: str,
        input_data: Dict[str, Any] = None,
        parent_span: Any = None
    ) -> Optional[Any]:
        """Create a span - simplified for v3 API.
        
        Note: In v3, prefer using @observe decorator instead.
        This method logs metadata for debugging purposes.
        """
        # In v3, spans are created via @observe decorator
        # This method just logs for debugging
        logger.debug(f"[{self.name}] Span: {name}, input={input_data}")
        return {"name": name, "input": input_data}  # Return dummy for compatibility

    def score_current_task(
        self,
        success: bool,
        duration_ms: float = None,
        comment: str = None
    ) -> None:
        """Score the current task (v3 API).
        
        Must be called inside an @observe decorated function.
        """
        try:
            # Score success
            score_current(
                name="task_success",
                value=1.0 if success else 0.0,
                comment=comment
            )
            
            # Score latency if provided
            if duration_ms is not None:
                score_current(
                    name="latency_ms",
                    value=duration_ms
                )
        except Exception as e:
            logger.debug(f"[{self.name}] score_current_task: {e}")

    def track_event(self, name: str, metadata: Dict[str, Any] = None) -> None:
        """Track a discrete event (v3 API).
        
        Updates current observation with event metadata.
        """
        if not LANGFUSE_AVAILABLE:
            return
        
        try:
            update_current_observation(
                metadata={
                    f"event_{name}": metadata or {},
                    "event_timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            logger.debug(f"[{self.name}] Event tracked: {name}")
        except Exception as e:
            logger.debug(f"[{self.name}] track_event: {e}")

    async def _create_execution_record(self, task: "TaskContext") -> UUID:
        """Create AgentExecution record in database"""
        from app.services import ExecutionService
        from sqlmodel import Session
        from app.core.db import engine
        
        # Use ExecutionService for async-safe execution creation
        with Session(engine) as db:
            execution_service = ExecutionService(db)
            execution_id = await execution_service.create_execution(
                project_id=self.project_id,
                agent_name=self.name,
                agent_type=self.role_type,
                trigger_message_id=task.message_id if hasattr(task, 'message_id') else None,
                user_id=task.user_id if hasattr(task, 'user_id') else None,
                task_type=task.task_type.value if hasattr(task, 'task_type') and task.task_type else None,
                task_content_preview=task.content[:200] if task.content else None,
            )
        

        return execution_id
    
    async def _complete_execution_record(
        self, 
        result: Optional["TaskResult"] = None, 
        error: Optional[str] = None,
        error_traceback: Optional[str] = None,
        success: bool = True
    ):
        """Update execution record with completion data"""
        if not self._current_execution_id:
            return
        
        from app.services import ExecutionService
        from sqlmodel import Session
        from app.core.db import engine
        
        duration_ms = None
        if self._execution_start_time:
            duration_ms = int(
                (datetime.now(timezone.utc) - self._execution_start_time).total_seconds() * 1000
            )
        
        # Use ExecutionService for async-safe execution completion
        with Session(engine) as db:
            execution_service = ExecutionService(db)
            await execution_service.complete_execution(
                execution_id=self._current_execution_id,
                success=success,
                output=result.output if result else None,
                structured_data=result.structured_data if result else None,
                error=error,
                error_traceback=error_traceback,
                events=self._execution_events,
                duration_ms=duration_ms
            )
        
        logger.info(
            f"[{self.name}] Execution {self._current_execution_id} "
            f"{'completed' if success else 'failed'} in {duration_ms}ms with {len(self._execution_events)} events"
        )

    async def start(self) -> bool:
        """Start the agent's Kafka consumer and task queue worker.

        Called during agent initialization.
        
        Returns:
            True if started successfully, False otherwise
        """
        from app.agents.core.base_agent_consumer import BaseAgentInstanceConsumer

        try:
            # Start task queue worker
            self._queue_running = True
            self._queue_worker_task = asyncio.create_task(self._task_queue_worker())
            
            # Create consumer with wrapper that calls our handle_task
            self._consumer = AgentTaskConsumer(self)
            await self._consumer.start()


            return True
        except Exception as e:
            logger.error(f"[{self.name}] Failed to start consumer: {e}")
            return False

    async def stop(self) -> None:
        """Stop the agent's Kafka consumer and task queue worker.

        Called during shutdown.
        """
        # Stop queue worker
        self._queue_running = False
        if self._queue_worker_task:
            self._queue_worker_task.cancel()
            try:
                await self._queue_worker_task
            except asyncio.CancelledError:
                pass
        
        # Stop consumer
        if self._consumer:
            await self._consumer.stop()


    async def health_check(self) -> dict:
        """Check if agent is healthy.
        
        Returns:
            Dict with health status: {"healthy": bool, "reason": str}
        """
        try:
            # Check if consumer is running
            if not self._consumer:
                return {
                    "healthy": False,
                    "reason": "Consumer not started"
                }
            
            # Agent is healthy if it has a consumer
            return {
                "healthy": True,
                "reason": "Consumer running"
            }
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "healthy": False,
                "reason": f"Exception: {str(e)}"
            }

    # ===== Internal Methods =====

    async def _get_producer(self) -> KafkaProducer:
        """Get Kafka producer (lazy init).

        Returns:
            KafkaProducer instance
        """
        if self._producer is None:
            self._producer = await get_kafka_producer()
        return self._producer

    async def _task_queue_worker(self) -> None:
        """Worker loop that processes tasks from queue one by one.
        
        This ensures:
        - Tasks are processed sequentially (no concurrent execution)
        - No state overwrite (task_id, execution_id)
        - Proper busy status management
        """

        
        while self._queue_running:
            try:
                # Wait for next task (with timeout to check _queue_running)
                try:
                    task_data = await asyncio.wait_for(
                        self._task_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue  # Check if still running
                
                # Process task
                await self._execute_task(task_data)
                
                # Mark task as done in queue
                self._task_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info(f"[{self.name}] Task queue worker cancelled")
                break
            except Exception as e:
                logger.error(f"[{self.name}] Task queue worker error: {e}", exc_info=True)
        


    async def _process_router_task(self, task_data: Dict[str, Any]) -> None:
        """Enqueue task from router for processing.

        This is called by the Kafka consumer. It:
        1. Checks if queue has space
        2. Enqueues task for sequential processing
        3. Worker loop will process it

        Args:
            task_data: RouterTaskEvent as dict
        """
        task_id = task_data.get("task_id", "unknown")
        
        try:
            # Try to add to queue (non-blocking)
            self._task_queue.put_nowait(task_data)
            
            queue_size = self._task_queue.qsize()
            logger.info(
                f"[{self.name}] Task {task_id} enqueued "
                f"(queue: {queue_size}/{self._task_queue.maxsize})"
            )
            
        except asyncio.QueueFull:
            logger.error(
                f"[{self.name}] Task queue FULL! Rejecting task {task_id}. "
                f"Agent is overloaded ({self._task_queue.maxsize} tasks pending)"
            )
            # TODO: Publish task rejection event back to router

    async def _execute_task(self, task_data: Dict[str, Any]) -> None:
        """Execute a single task (called by worker loop) with execution tracking.

        This is the actual task execution logic. It:
        1. Converts RouterTaskEvent → TaskContext
        2. Creates AgentExecution record
        3. Calls agent's handle_task()
        4. Updates execution record with result
        5. Publishes response

        Args:
            task_data: RouterTaskEvent as dict
        """
        try:
            # Extract task info
            task_id = task_data.get("task_id")
            self._current_task_id = task_id
            self._current_trace_id = str(task_id)  # Use task_id as trace identifier
            
            # Extract context
            context = task_data.get("context", {})
            
            # Track task context for clarification questions
            self._current_task_type = task_data.get("task_type", "message")
            self._current_task_content = context.get("content", "")
            self._current_routing_reason = task_data.get("routing_reason", "")
            # user_id can be at top-level (RouterTaskEvent) or in context
            self._current_user_id = task_data.get("user_id") or context.get("user_id")
            if self._current_user_id and isinstance(self._current_user_id, str):
                self._current_user_id = UUID(self._current_user_id)

            # Handle collaboration task types separately (don't create full TaskContext)
            task_type_str = task_data.get("task_type", "message")
            
            if task_type_str == "collaboration_request":
                # Handle incoming collaboration request
                logger.info(f"[{self.name}] Handling collaboration request")
                try:
                    response = await self.handle_collaboration_request(
                        request_id=UUID(context.get("request_id")),
                        question=context.get("question", ""),
                        request_type=context.get("request_type", "clarification"),
                        from_agent_role=context.get("from_agent_role", "unknown"),
                        context=context.get("collaboration_context", {})
                    )
                    
                    # Send response back
                    await self._send_collaboration_response(
                        request_id=context.get("request_id"),
                        to_agent_id=context.get("from_agent_id"),
                        response=response,
                        success=True
                    )
                except Exception as e:
                    logger.error(f"[{self.name}] Collaboration request handling failed: {e}")
                    await self._send_collaboration_response(
                        request_id=context.get("request_id"),
                        to_agent_id=context.get("from_agent_id"),
                        response="",
                        success=False,
                        error=str(e)
                    )
                finally:
                    self._current_task_id = None
                return
            
            elif task_type_str == "collaboration_response":
                # Handle incoming collaboration response (resume waiting agent)
                logger.info(f"[{self.name}] Handling collaboration response")
                await self._handle_collaboration_response(
                    request_id=UUID(context.get("request_id")),
                    response=context.get("response", ""),
                    success=context.get("success", True),
                    error=context.get("error")
                )
                self._current_task_id = None
                return
            
            # Create TaskContext for normal task processing
            task = TaskContext(
                task_id=task_id,
                task_type=AgentTaskType(task_type_str),
                priority=task_data.get("priority", "medium"),
                routing_reason=task_data.get("routing_reason", ""),
                message_id=context.get("message_id"),
                user_id=context.get("user_id"),
                project_id=context.get("project_id") or self.project_id,
                content=context.get("content", ""),
                message_type=context.get("message_type", "text"),
                execution_mode=context.get("execution_mode", "interactive"),  # NEW: Get execution mode
                context=context,
            )
            
            # Set current execution mode for display_mode logic
            self._current_execution_mode = task.execution_mode
           
            # Create execution record in database
            self._current_execution_id = await self._create_execution_record(task)
            self._execution_start_time = datetime.now(timezone.utc)
            self._execution_events.clear()

            logger.info(
                f"[{self.name}] Processing task {task_id} (execution={self._current_execution_id}): "
                f"type={task.task_type}, reason={task.routing_reason}"
            )

            # Update state to busy
            self.state = AgentStatus.busy
            
            # CHECK TOKEN BUDGET BEFORE PROCESSING
            estimated_tokens = self._estimate_task_tokens(task)
            budget_allowed, budget_reason = await self._check_token_budget(estimated_tokens)
            
            if not budget_allowed:
                # Budget exceeded - reject task
                logger.warning(
                    f"[{self.name}] Task {task_id} rejected: {budget_reason}"
                )
                
                await self.message_user(
                    "error",
                    f"⚠️ **Token Budget Exceeded**\n\n{budget_reason}\n\n"
                    f"Please contact your project admin or try again later.",
                    {"budget_exceeded": True, "reason": budget_reason}
                )
                
                # Update execution record with budget error
                await self._complete_execution_record(
                    error=budget_reason,
                    success=False
                )
                
                # Return to idle
                self.state = AgentStatus.idle
                return
            
            # Emit "thinking" status ONCE - agents can send custom thinking messages in handle_task
            await self.message_user("thinking", f"Processing request...")

            task_failed = False
            try:
                # Call agent's implementation
                result = await self.handle_task(task)
                
                # Record actual token usage
                actual_tokens = self._extract_token_usage(result)
                if actual_tokens > 0:
                    await self._record_token_usage(actual_tokens)
                
                
                # Update execution record with success
                await self._complete_execution_record(result=result, success=True)
                
                # Update statistics
                self.total_executions += 1
                if result.success:
                    self.successful_executions += 1
                else:
                    self.failed_executions += 1
                
                # Emit finish signal (commented out to avoid duplicate messages)
                # if result.success:
                #     await self.finish_execution("Task completed successfully")
                # else:
                #     await self.finish_execution(f"Task completed with issues: {result.error_message or 'Unknown'}")
                
            except Exception as e:
                task_failed = True
                
                # Emit error status to frontend
                await self.message_user("error", f"Task failed: {str(e)}", {
                    "error_type": type(e).__name__
                })
                
                # Update execution record with failure
                await self._complete_execution_record(
                    error=str(e),
                    error_traceback=traceback.format_exc(),
                    success=False
                )
                
                # Emit finish signal with error

                await self.finish_execution(f"Task failed: {str(e)[:100]}")
                
                raise  # Re-raise to let outer handler deal with it
            
            finally:
                # Return to idle
                self.state = AgentStatus.idle
                
                # Emit "idle" status to clear frontend indicator (only if no error)
                if not task_failed:
                    await self.message_user("idle", "Task completed")

            # Log completion (only if task didn't raise exception)
            if not task_failed:
                if result   .success:
                    pass
                else:
                    logger.error(
                        f"[{self.name}] Task {task_id} failed: {result.error_message}"
                    )

        except Exception as e:
            logger.error(
                f"[{self.name}] Error processing task {task_id}: {e}",
                exc_info=True
            )
        finally:
            # Score task completion (v3 API - non-blocking)
            try:
                duration_ms = (datetime.now(timezone.utc) - self._execution_start_time).total_seconds() * 1000 if self._execution_start_time else 0
                task_success = not task_failed if 'task_failed' in locals() else True
                self.score_current_task(success=task_success, duration_ms=duration_ms)
                flush_langfuse()
            except Exception as e:
                logger.debug(f"[{self.name}] Langfuse cleanup: {e}")
            
            # Reset task state
            self._current_task_id = None
            self._current_execution_id = None
            self._current_trace_id = None
            self._current_trace = None
    
    # ===== Token Budget Methods =====
    
    def _estimate_task_tokens(self, task: TaskContext) -> int:
        """Estimate tokens needed for task.
        
        Simple estimation based on content length and task type.
        For more accurate estimation, subclasses can override this.
        
        Args:
            task: Task context
            
        Returns:
            Estimated tokens (conservative estimate)
        """
        # Base estimate from content length
        # Rough approximation: 1 token ~= 4 characters for English
        content_tokens = len(task.content) // 4
        
        # Task type multipliers (accounts for processing complexity)
        multipliers = {
            AgentTaskType.MESSAGE: 500,  # Simple messages
            AgentTaskType.ANALYZE_REQUIREMENTS: 2000,  # Analysis tasks
            AgentTaskType.CREATE_STORIES: 1500,
            AgentTaskType.IMPLEMENT_STORY: 3000,  # Code generation
            AgentTaskType.WRITE_TESTS: 2000,
            AgentTaskType.CODE_REVIEW: 1500,
            AgentTaskType.FIX_BUG: 2000,
            AgentTaskType.REFACTOR: 2500,
            AgentTaskType.RESUME_WITH_ANSWER: 1000,
        }
        
        base_estimate = multipliers.get(task.task_type, 1000)
        
        # Total estimate: base + content-based
        estimated = base_estimate + content_tokens
        
        logger.debug(
            f"[{self.name}] Estimated {estimated:,} tokens for task "
            f"(type={task.task_type.value}, content_len={len(task.content)})"
        )
        
        return estimated
    
    def _extract_token_usage(self, result: TaskResult) -> int:
        """Extract actual token usage from task result.
        
        Looks for token usage in structured_data or estimates from output.
        
        Args:
            result: Task result
            
        Returns:
            Actual tokens used (0 if not available)
        """
        if not result:
            return 0
        
        # Check structured_data for token_usage field
        if result.structured_data:
            tokens = result.structured_data.get("token_usage") or \
                    result.structured_data.get("tokens_used") or \
                    result.structured_data.get("total_tokens")
            
            if tokens and isinstance(tokens, int):
                return tokens
        
        # Fallback: Estimate from output length
        if result.output:
            estimated = len(result.output) // 4
            logger.debug(
                f"[{self.name}] Estimated {estimated:,} tokens from output length "
                f"(no explicit token_usage in result)"
            )
            return estimated
        
        return 0
    
    async def _check_token_budget(self, estimated_tokens: int) -> Tuple[bool, str]:
        """Check if project has token budget for task.
        
        Args:
            estimated_tokens: Estimated tokens needed
            
        Returns:
            Tuple of (allowed, reason)
        """
        if not self.project_id:
            # No project - allow (shouldn't happen in production)
            return True, ""
        
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.services.token_budget_service import TokenBudgetManager
            
            with Session(engine) as session:
                budget_mgr = TokenBudgetManager(session)
                allowed, reason = await budget_mgr.check_budget(
                    self.project_id,
                    estimated_tokens
                )
                
                return allowed, reason
                
        except Exception as e:
            logger.error(
                f"[{self.name}] Error checking token budget: {e}", 
                exc_info=True
            )
            # Fail open - allow task on error to avoid blocking
            return True, ""
    
    async def _record_token_usage(self, tokens_used: int) -> None:
        """Record actual token usage.
        
        Args:
            tokens_used: Actual tokens consumed
        """
        if not self.project_id:
            return
        
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.services.token_budget_service import TokenBudgetManager
            
            with Session(engine) as session:
                budget_mgr = TokenBudgetManager(session)
                await budget_mgr.record_usage(self.project_id, tokens_used)
                
        except Exception as e:
            logger.error(
                f"[{self.name}] Error recording token usage: {e}",
                exc_info=True
            )


class AgentTaskConsumer:
    """Internal consumer wrapper that connects BaseAgent to Kafka.

    This is an implementation detail - agents don't interact with this directly.
    """

    def __init__(self, agent: BaseAgent):
        """Initialize consumer wrapper.

        Args:
            agent: BaseAgent instance to process tasks for
        """
        self.agent = agent
        self._consumer_instance = None

    async def start(self) -> None:
        """Start consuming tasks from Kafka."""
        from app.agents.core.base_agent_consumer import BaseAgentInstanceConsumer

        # Create a dynamic consumer class that wraps the agent
        class DynamicConsumer(BaseAgentInstanceConsumer):
            def __init__(inner_self, agent_model: AgentModel, base_agent: BaseAgent):
                super().__init__(agent_model)
                inner_self.base_agent = base_agent

            async def process_task(inner_self, task_data: Dict[str, Any]) -> None:
                """Delegate to BaseAgent's _process_router_task."""
                await inner_self.base_agent._process_router_task(task_data)

        # Create consumer instance
        self._consumer_instance = DynamicConsumer(self.agent.agent_model, self.agent)

        # Start consumer
        await self._consumer_instance.start()

    async def stop(self) -> None:
        """Stop consuming tasks."""
        if self._consumer_instance:
            await self._consumer_instance.stop()
