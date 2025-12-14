"""Team Leader Agent - LangGraph-based Routing."""

import logging
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.core.agent.base_agent import BaseAgent, TaskContext, TaskResult
from app.core.agent.project_context import ProjectContext
from app.models import Agent as AgentModel, ArtifactType, Epic, Story, Project
from app.agents.team_leader.src import TeamLeaderGraph, generate_response_message, check_cancel_intent
from app.kafka.event_schemas import AgentTaskType
from app.core.db import engine
from app.services.artifact_service import ArtifactService
from app.utils.project_files import ProjectFiles

logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader using LangGraph for intelligent routing."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Team Leader Agent")
        
        # Shared project context (memory + preferences)
        self.context = ProjectContext.get(self.project_id)
        
        # Initialize project files for archiving
        self.project_files = None
        if self.project_id:
            with Session(engine) as session:
                project = session.get(Project, self.project_id)
                if project and project.project_path:
                    self.project_files = ProjectFiles(Path(project.project_path))
                else:
                    default_path = Path("projects") / str(self.project_id)
                    default_path.mkdir(parents=True, exist_ok=True)
                    self.project_files = ProjectFiles(default_path)
        
        # Pass self to graph for delegation and Langfuse callback access
        self.graph_engine = TeamLeaderGraph(agent=self)
        
        logger.info(f"[{self.name}] LangGraph initialized")
    
    async def update_preference(self, key: str, value) -> bool:
        """Update a single preference in DB and shared cache."""
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import ProjectPreference
            
            with Session(engine) as session:
                pref = session.query(ProjectPreference).filter(
                    ProjectPreference.project_id == self.project_id
                ).first()
                
                if not pref:
                    pref = ProjectPreference(
                        project_id=self.project_id,
                        preferences={key: value}
                    )
                    session.add(pref)
                else:
                    current = pref.preferences or {}
                    current[key] = value
                    pref.preferences = current
                
                session.commit()
                
                # Update shared cache
                self.context.update_preference(key, value)
                logger.info(f"[{self.name}] Updated preference: {key} = {value}")
                return True
                
        except Exception as e:
            logger.error(f"[{self.name}] Failed to update preference: {e}")
            return False

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph with conversation memory."""
        logger.info(f"[{self.name}] Processing task: {task.content[:50]}")
        
        # Check if this is a resume task (user answered a question)
        is_resume = task.task_type == AgentTaskType.RESUME_WITH_ANSWER
        
        if is_resume:
            # For multichoice, answer is in selected_options
            context = task.context or {}
            answer = context.get("answer", "")
            selected_options = context.get("selected_options", [])
            
            # Use selected_options if answer is empty (multichoice case)
            if not answer and selected_options:
                answer = selected_options[0] if isinstance(selected_options, list) else str(selected_options)
            
            logger.info(f"[{self.name}] Processing RESUME task with answer: {answer[:50] if answer else 'empty'}")
            return await self._handle_resume_task(task, answer)
        
        # Load shared context (cached, parallel loading)
        await self.context.ensure_loaded()
        
        try:
            # 1. Add user message to shared memory
            self.context.add_message("user", task.content)
            
            # 2. Setup Langfuse tracing (1 trace for entire graph)
            langfuse_handler = None
            langfuse_span = None
            langfuse_ctx = None
            
            # Check if Langfuse is enabled before initializing
            from app.core.config import settings
            if settings.LANGFUSE_ENABLED:
                try:
                    from langfuse import get_client
                    from langfuse.langchain import CallbackHandler
                    langfuse = get_client()
                    # Create parent span for entire graph execution
                    langfuse_ctx = langfuse.start_as_current_observation(
                        as_type="span",
                        name="team_leader_graph"
                    )
                    # Enter context and get span object
                    langfuse_span = langfuse_ctx.__enter__()
                    # Update trace with metadata (on span, not context)
                    langfuse_span.update_trace(
                        user_id=str(task.user_id) if task.user_id else None,
                        session_id=str(self.project_id),
                        input={"message": task.content[:200]},
                        tags=["team_leader", self.role_type],
                        metadata={"agent": self.name, "task_id": str(task.task_id)}
                    )
                    # Handler inherits trace context automatically
                    langfuse_handler = CallbackHandler()
                except Exception as e:
                    logger.debug(f"Langfuse setup: {e}")
            
            # 3. Build state
            initial_state = {
                "user_message": task.content,
                "user_id": str(task.user_id) if task.user_id else "",
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "conversation_history": self.context.format_memory(),
                "user_preferences": self.context.format_preferences(),
                "attachments": task.context.get("attachments") if task.context else None,  # Pass file attachments
                "action": None,
                "target_role": None,
                "message": None,
                "reason": None,
                "confidence": None,
                "wip_blocked": None,
                "langfuse_handler": langfuse_handler,
            }
            
            # 4. Execute graph
            logger.info(f"[{self.name}] Invoking LangGraph...")
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
            # 5. Update trace output and close span
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output={
                        "action": final_state.get("action"),
                        "target_role": final_state.get("target_role"),
                    })
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            action = final_state.get("action")
            confidence = final_state.get("confidence")
            target_role = final_state.get("target_role")
            wip_blocked = final_state.get("wip_blocked", False)
            response_msg = final_state.get("message", "")
            
            # 6. Add response to shared memory
            if response_msg:
                self.context.add_message("assistant", response_msg)
            
            logger.info(
                f"[{self.name}] Graph completed: action={action}, "
                f"confidence={confidence}, wip_blocked={wip_blocked}"
            )
            
            return TaskResult(
                success=True,
                output=response_msg,
                structured_data={
                    "action": action,
                    "target_role": target_role,
                    "reason": final_state.get("reason"),
                    "confidence": confidence,
                    "wip_blocked": wip_blocked,
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] LangGraph error: {e}", exc_info=True)
            # Cleanup langfuse on error
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                except Exception:
                    pass
            return TaskResult(
                success=False,
                output="",
                error_message=f"Graph execution error: {str(e)}"
            )
    
    async def _handle_resume_task(self, task: TaskContext, answer: str) -> TaskResult:
        """Handle resume task - user answered question for project confirmation."""
        try:
            # Check if this is a project confirmation
            routing_reason = task.routing_reason or ""
            
            if "question_answer" not in routing_reason:
                logger.warning(f"[{self.name}] Unknown resume task: {routing_reason}")
                return TaskResult(success=False, output="", error_message="Unknown resume task type")
            
            # Check if this is an answer to "ASK_NEW_FEATURE" question
            original_context = task.context.get("original_context", {})
            question_context = original_context.get("question_context", {})
            question_type = question_context.get("question_type", "")
            
            if question_type == "ASK_NEW_FEATURE":
                # User is answering what feature to add - pass the answer
                return await self._handle_new_feature_answer(task, answer)
            
            # Parse user's choice
            answer_lower = answer.lower().strip()
            
            # Check for CONFIRM_EXISTING options (same domain)
            is_view = "xem" in answer_lower and ("prd" in answer_lower or "stories" in answer_lower or "hiện tại" in answer_lower)
            is_update = "cập nhật" in answer_lower or "thêm feature" in answer_lower or "thêm" in answer_lower
            is_recreate = "tạo lại" in answer_lower or "từ đầu" in answer_lower
            
            # Check for CONFIRM_REPLACE options (different domain)
            is_replace = "thay thế" in answer_lower or "project mới" in answer_lower
            
            logger.info(f"[{self.name}] User chose: view={is_view}, update={is_update}, recreate={is_recreate}, replace={is_replace} (answer: {answer})")
            
            # Handle VIEW existing
            if is_view:
                return await self._handle_view_existing(task)
            
            # Handle UPDATE/ADD features
            if is_update:
                return await self._handle_update_existing(task)
            
            # Handle RECREATE or REPLACE (delete and create new)
            if is_recreate or is_replace:
                # Delete existing PRD, Epics, Stories
                await self._delete_existing_project_data()
                
                # Get original user message and attachments for context
                original_context = task.context.get("original_context", {})
                question_context = original_context.get("question_context", {})
                original_message = (
                    question_context.get("original_user_message") or
                    original_context.get("original_message") or
                    task.content or
                    "Tạo project mới"
                )
                
                # IMPORTANT: Get original attachments to pass to BA
                original_attachments = (
                    question_context.get("attachments") or
                    original_context.get("attachments") or
                    []
                )
                
                logger.info(f"[{self.name}] Original attachments found: {len(original_attachments)}")
                if original_attachments:
                    for i, att in enumerate(original_attachments):
                        logger.info(f"[{self.name}] Attachment[{i}]: {att.get('filename')}, text_len={len(att.get('extracted_text', ''))}")
                
                # Show typing indicator while generating response (LLM call takes ~10s)
                await self.message_user("thinking", "Đang xử lý yêu cầu...")
                
                # Generate and send response - mention BA delegation
                msg = await generate_response_message(
                    action="replace",
                    context="User chọn thay thế project cũ. Đã xóa dữ liệu cũ và đang chuyển cho Business Analyst để phân tích yêu cầu mới",
                    extra_info=f"Yêu cầu của user: {original_message}",
                    agent=self
                )
                logger.info(f"[{self.name}] Generated replace response: {msg[:100] if msg else 'EMPTY'}...")
                await self.message_user("response", msg, display_mode="chat")  # Force chat mode
                logger.info(f"[{self.name}] Sent replace response to user")
                
                # Delegate to BA for new project with attachments
                logger.info(f"[{self.name}] Delegating to BA with message: {original_message[:50] if original_message else 'empty'}...")
                logger.info(f"[{self.name}] Passing {len(original_attachments)} attachment(s) to BA")
                
                # Build context with attachments and conversation history
                new_task_context = {}
                if original_attachments:
                    new_task_context["attachments"] = original_attachments
                
                # Pass conversation history for BA to understand context
                conversation_history = self.context.format_memory()
                if conversation_history:
                    new_task_context["conversation_history"] = conversation_history
                    logger.info(f"[{self.name}] Passing conversation history ({len(conversation_history)} chars) to BA")
                
                new_task = TaskContext(
                    task_id=task.task_id,
                    task_type=AgentTaskType.MESSAGE,
                    priority="high",
                    routing_reason="project_replace_confirmed",
                    user_id=task.user_id,
                    project_id=self.project_id,
                    content=original_message,
                    context=new_task_context if new_task_context else None,
                )
                await self.delegate_to_role(
                    task=new_task,
                    target_role="business_analyst",
                    delegation_message=msg
                )
                
                return TaskResult(
                    success=True,
                    output=msg,
                    structured_data={"action": "DELEGATE", "target_role": "business_analyst", "replaced": True}
                )
            
            # Default: Keep existing project (for CONFIRM_REPLACE - "Giữ nguyên project cũ")
            # Show typing indicator while generating response
            await self.message_user("thinking", "Đang xử lý...")
            
            msg = await generate_response_message(
                action="keep",
                context="User chọn giữ nguyên project cũ, không thay đổi gì",
                agent=self
            )
            logger.info(f"[{self.name}] Generated keep response: {msg[:100] if msg else 'EMPTY'}...")
            await self.message_user("response", msg, display_mode="chat")  # Force chat mode
            logger.info(f"[{self.name}] Sent keep response to user")
            
            return TaskResult(
                success=True,
                output=msg,
                structured_data={"action": "RESPOND", "replaced": False}
            )
                
        except Exception as e:
            logger.error(f"[{self.name}] Error handling resume task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Resume task error: {str(e)}"
            )
    
    async def _delete_existing_project_data(self):
        """Delete existing PRD, Epics, and Stories for the project."""
        try:
            from sqlmodel import select
            
            with Session(engine) as session:
                # Delete PRD artifact
                artifact_service = ArtifactService(session)
                prd_count = artifact_service.delete_by_type(self.project_id, ArtifactType.PRD)
                stories_artifact_count = artifact_service.delete_by_type(self.project_id, ArtifactType.USER_STORIES)
                
                # Delete Epics (cascade deletes Stories)
                epics = session.exec(
                    select(Epic).where(Epic.project_id == self.project_id)
                ).all()
                
                for epic in epics:
                    session.delete(epic)
                
                # Delete Stories that might not be linked to epics
                stories = session.exec(
                    select(Story).where(Story.project_id == self.project_id)
                ).all()
                
                for story in stories:
                    session.delete(story)
                
                session.commit()
                
                logger.info(
                    f"[{self.name}] Deleted project data: "
                    f"{prd_count} PRD artifacts, {stories_artifact_count} stories artifacts, "
                    f"{len(epics)} epics, {len(stories)} stories"
                )
            
            # Archive docs files (move to docs/archive/)
            if self.project_files:
                await self.project_files.archive_docs()
                logger.info(f"[{self.name}] Archived docs files to docs/archive/")
            
            # Send WebSocket notification to refresh Kanban board
            # Note: save_to_db=False to avoid creating empty message in DB
            await self.message_user(
                event_type="response",
                content="",  # No visible message, just trigger refresh
                details={
                    "message_type": "project_reset",  # Frontend will refresh Kanban
                    "deleted_epics": len(epics),
                    "deleted_stories": len(stories),
                },
                save_to_db=False,  # Don't save to DB, just broadcast via WebSocket
            )
            logger.info(f"[{self.name}] Sent project_reset notification to frontend")
                
        except Exception as e:
            logger.error(f"[{self.name}] Error deleting project data: {e}", exc_info=True)
            raise

    async def _handle_view_existing(self, task: TaskContext) -> TaskResult:
        """Handle user request to view existing PRD and Stories."""
        try:
            from sqlmodel import select
            
            with Session(engine) as session:
                # Get PRD
                artifact_service = ArtifactService(session)
                prd = artifact_service.get_latest_version(
                    project_id=self.project_id,
                    artifact_type=ArtifactType.PRD
                )
                
                # Get Stories count
                stories = session.exec(
                    select(Story).where(Story.project_id == self.project_id)
                ).all()
                
                if prd:
                    msg = await generate_response_message(
                        action="view",
                        context="User muốn xem thông tin project hiện tại",
                        extra_info=f"PRD: {prd.title}, Stories: {len(stories)}. Có thể xem chi tiết trong tab Documents",
                        agent=self
                    )
                else:
                    msg = await generate_response_message(
                        action="view",
                        context="Không tìm thấy PRD nào trong project",
                        extra_info="Hỏi user có muốn tạo mới không",
                        agent=self
                    )
                
                await self.message_user("response", msg)
                
                return TaskResult(
                    success=True,
                    output=msg,
                    structured_data={"action": "RESPOND", "viewed": True}
                )
                
        except Exception as e:
            logger.error(f"[{self.name}] Error viewing existing: {e}", exc_info=True)
            msg = "Có lỗi khi tải thông tin project. Vui lòng thử lại! 😅"
            await self.message_user("response", msg)
            return TaskResult(success=False, output=msg, error_message=str(e))

    async def _handle_update_existing(self, task: TaskContext) -> TaskResult:
        """Handle user request to update/add features to existing project.
        
        This asks user WHAT feature they want to add, then waits for their answer.
        """
        try:
            # Get original context
            original_context = task.context.get("original_context", {})
            question_context = original_context.get("question_context", {})
            existing_title = question_context.get("existing_prd_title", "project hiện tại")
            
            # Get attachments if any
            attachments = (
                question_context.get("attachments") or
                original_context.get("attachments") or
                []
            )
            
            # Ask user what feature they want to add
            question = f"Bạn muốn thêm/cập nhật feature gì cho dự án \"{existing_title}\"?\n\nMô tả chi tiết feature bạn muốn thêm nhé! 📝"
            
            # Save context for when user answers
            new_question_context = {
                "question_type": "ASK_NEW_FEATURE",
                "existing_prd_title": existing_title,
                "attachments": attachments
            }
            
            await self.message_user(
                "question",
                question,
                question_config={
                    "type": "text",
                    "context": new_question_context
                }
            )
            
            logger.info(f"[{self.name}] Asked user what feature to add to '{existing_title}'")
            
            return TaskResult(
                success=True,
                output=question,
                structured_data={"action": "ASK_NEW_FEATURE", "waiting_for_answer": True}
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Error handling update: {e}", exc_info=True)
            msg = "Có lỗi xảy ra. Vui lòng thử lại! 😅"
            await self.message_user("response", msg)
            return TaskResult(success=False, output=msg, error_message=str(e))
    
    async def _handle_new_feature_answer(self, task: TaskContext, answer: str) -> TaskResult:
        """Handle user's answer about what feature to add."""
        try:
            # Get the feature description from user's answer (passed from _handle_resume_task)
            feature_description = (answer or task.content or "").strip()
            
            if not feature_description:
                await self.message_user(
                    "response",
                    "Bạn chưa mô tả feature muốn thêm. Hãy cho mình biết bạn muốn thêm feature gì nhé! 📝"
                )
                return TaskResult(success=False, output="Empty feature description")
            
            # Check for cancel/no-change intent using LLM
            is_cancel = await check_cancel_intent(feature_description, agent=self)
            
            if is_cancel:
                logger.info(f"[{self.name}] User cancelled feature update: {feature_description}")
                await self.message_user(
                    "response",
                    "OK! Mình sẽ giữ nguyên PRD hiện tại. Nếu cần thêm feature sau, cứ nói với mình nhé! 👍"
                )
                return TaskResult(
                    success=True,
                    output="User cancelled feature update",
                    structured_data={"action": "cancelled"}
                )
            
            logger.info(f"[{self.name}] User wants to add feature: {feature_description[:100]}...")
            
            # Get context
            original_context = task.context.get("original_context", {})
            question_context = original_context.get("question_context", {})
            existing_title = question_context.get("existing_prd_title", "project hiện tại")
            attachments = question_context.get("attachments", [])
            
            # Generate response
            feature_preview = feature_description[:50] + "..." if len(feature_description) > 50 else feature_description
            msg = f"Đã ghi nhận! 📝 Mình sẽ chuyển cho BA để cập nhật PRD với feature mới: \"{feature_preview}\" nhé!"
            await self.message_user("response", msg)
            
            # Build context with metadata for update mode
            new_task_context = {
                "is_update_mode": True,
                "existing_prd_title": existing_title,
                "feature_to_add": feature_description,
            }
            if attachments:
                new_task_context["attachments"] = attachments
            
            # Pass conversation history for BA to understand context
            conversation_history = self.context.format_memory()
            if conversation_history:
                new_task_context["conversation_history"] = conversation_history
                logger.info(f"[{self.name}] Passing conversation history ({len(conversation_history)} chars) to BA")
            
            # Delegate to BA with update context
            new_task = TaskContext(
                task_id=task.task_id,
                task_type=AgentTaskType.MESSAGE,
                priority="high",
                routing_reason="update_existing_project",
                user_id=task.user_id,
                project_id=self.project_id,
                content=feature_description,  # Clean content without prefix
                context=new_task_context
            )
            
            await self.delegate_to_role(
                task=new_task,
                target_role="business_analyst",
                delegation_message=msg
            )
            
            logger.info(f"[{self.name}] Delegated feature update to BA: {feature_description[:50]}...")
            
            return TaskResult(
                success=True,
                output=msg,
                structured_data={"action": "DELEGATE", "target_role": "business_analyst", "update_mode": True}
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Error handling new feature: {e}", exc_info=True)
            msg = "Có lỗi xảy ra. Vui lòng thử lại! 😅"
            await self.message_user("response", msg)
            return TaskResult(success=False, output=msg, error_message=str(e))
    
