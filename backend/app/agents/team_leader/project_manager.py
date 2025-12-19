"""Project management operations for Team Leader."""

import logging
from typing import TYPE_CHECKING

from sqlmodel import Session, select
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.core.llm_factory import get_llm
from app.agents.core.base_agent import TaskContext, TaskResult
from app.models import ArtifactType, Epic, Story
from app.core.db import engine
from app.services.artifact_service import ArtifactService
from app.kafka.event_schemas import AgentTaskType
from app.agents.team_leader.src.schemas import ConfirmationAction
from app.agents.team_leader.src import generate_response_message, check_cancel_intent

if TYPE_CHECKING:
    from app.agents.team_leader.team_leader import TeamLeader

logger = logging.getLogger(__name__)


class ProjectManager:
    """Handles project CRUD operations and user confirmations."""
    
    def __init__(self, agent: "TeamLeader"):
        self.agent = agent
    
    async def handle_confirmation_answer(
        self, 
        task: TaskContext, 
        answer: str
    ) -> TaskResult:
        """Main entry point for handling user's confirmation answer."""
        try:
            # Check if this is ASK_NEW_FEATURE question
            original_context = task.context.get("original_context", {})
            question_context = original_context.get("question_context", {})
            question_type = question_context.get("question_type", "")
            
            if question_type == "ASK_NEW_FEATURE":
                return await self._handle_new_feature_answer(task, answer)
            
            # Parse user's choice using LLM (Phương án 2)
            action = await self._parse_confirmation_choice(answer)
            
            # Route to appropriate handler
            if action == "view":
                return await self._handle_view_existing(task)
            elif action == "update":
                return await self._handle_update_existing(task)
            elif action == "replace":
                return await self._handle_replace_existing(task)
            else:  # keep
                return await self._handle_keep_existing(task)
                
        except Exception as e:
            logger.error(f"[ProjectManager] Error handling confirmation: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Confirmation error: {str(e)}"
            )
    
    async def _parse_confirmation_choice(self, answer: str) -> str:
        """Parse user's answer using LLM (Phương án 2)."""
        try:
            system_prompt = """Bạn là AI phân tích câu trả lời của user về việc xử lý project.

Phân loại câu trả lời thành 1 trong 4 actions:
- "view": User muốn XEM PRD/stories hiện tại
- "update": User muốn THÊM/CẬP NHẬT feature cho project hiện tại
- "replace": User muốn THAY THẾ/TẠO LẠI project hoàn toàn mới
- "keep": User muốn GIỮ NGUYÊN, không thay đổi gì"""

            structured_llm = get_llm("router").with_structured_output(ConfirmationAction)
            result = await structured_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User answer: {answer}")
            ])
            
            logger.info(
                f"[ProjectManager] Parsed '{answer[:50]}' -> action={result.action}, "
                f"confidence={result.confidence}"
            )
            
            return result.action
            
        except Exception as e:
            logger.error(f"[ProjectManager] LLM parse error: {e}, falling back to 'keep'")
            return "keep"
    
    async def delete_project_data(self):
        """Delete existing PRD, Epics, and Stories."""
        try:
            with Session(engine) as session:
                artifact_service = ArtifactService(session)
                prd_count = artifact_service.delete_by_type(
                    self.agent.project_id, 
                    ArtifactType.PRD
                )
                stories_artifact_count = artifact_service.delete_by_type(
                    self.agent.project_id, 
                    ArtifactType.USER_STORIES
                )
                
                epics = session.exec(
                    select(Epic).where(Epic.project_id == self.agent.project_id)
                ).all()
                
                for epic in epics:
                    session.delete(epic)
                
                stories = session.exec(
                    select(Story).where(Story.project_id == self.agent.project_id)
                ).all()
                
                for story in stories:
                    session.delete(story)
                
                session.commit()
                
                logger.info(
                    f"[ProjectManager] Deleted: {prd_count} PRD, "
                    f"{stories_artifact_count} stories artifacts, "
                    f"{len(epics)} epics, {len(stories)} stories"
                )
            
            # Archive docs
            if self.agent.project_files:
                await self.agent.project_files.archive_docs()
                logger.info("[ProjectManager] Archived docs to docs/archive/")
            
            # Notify frontend
            await self.agent.message_user(
                event_type="response",
                content="",
                details={
                    "message_type": "project_reset",
                    "deleted_epics": len(epics),
                    "deleted_stories": len(stories),
                },
                save_to_db=False,
            )
            
        except Exception as e:
            logger.error(f"[ProjectManager] Delete error: {e}", exc_info=True)
            raise
    
    async def _handle_view_existing(self, task: TaskContext) -> TaskResult:
        """Handle view existing PRD request."""
        try:
            with Session(engine) as session:
                artifact_service = ArtifactService(session)
                prd = artifact_service.get_latest_version(
                    project_id=self.agent.project_id,
                    artifact_type=ArtifactType.PRD
                )
                
                stories = session.exec(
                    select(Story).where(Story.project_id == self.agent.project_id)
                ).all()
                
                if prd:
                    msg = await generate_response_message(
                        action="view",
                        context="User muốn xem thông tin project hiện tại",
                        extra_info=f"PRD: {prd.title}, Stories: {len(stories)}",
                        agent=self.agent
                    )
                else:
                    msg = await generate_response_message(
                        action="view",
                        context="Không tìm thấy PRD",
                        extra_info="Hỏi user có muốn tạo mới không",
                        agent=self.agent
                    )
                
                await self.agent.message_user("response", msg)
                
                return TaskResult(
                    success=True,
                    output=msg,
                    structured_data={"action": "RESPOND", "viewed": True}
                )
                
        except Exception as e:
            logger.error(f"[ProjectManager] View error: {e}", exc_info=True)
            msg = "Có lỗi khi tải thông tin project. Vui lòng thử lại! 😅"
            await self.agent.message_user("response", msg)
            return TaskResult(success=False, output=msg, error_message=str(e))
    
    async def _handle_update_existing(self, task: TaskContext) -> TaskResult:
        """Handle update/add feature request."""
        try:
            original_context = task.context.get("original_context", {})
            question_context = original_context.get("question_context", {})
            existing_title = question_context.get("existing_prd_title", "project hiện tại")
            attachments = (
                question_context.get("attachments") or
                original_context.get("attachments") or
                []
            )
            
            question = f"Bạn muốn thêm/cập nhật feature gì cho dự án \"{existing_title}\"?\n\nMô tả chi tiết feature bạn muốn thêm nhé! 📝"
            
            await self.agent.message_user(
                "question",
                question,
                question_config={
                    "type": "text",
                    "context": {
                        "question_type": "ASK_NEW_FEATURE",
                        "existing_prd_title": existing_title,
                        "attachments": attachments
                    }
                }
            )
            
            logger.info(f"[ProjectManager] Asked user what feature to add to '{existing_title}'")
            
            return TaskResult(
                success=True,
                output=question,
                structured_data={"action": "ASK_NEW_FEATURE", "waiting_for_answer": True}
            )
            
        except Exception as e:
            logger.error(f"[ProjectManager] Update error: {e}", exc_info=True)
            msg = "Có lỗi xảy ra. Vui lòng thử lại! 😅"
            await self.agent.message_user("response", msg)
            return TaskResult(success=False, output=msg, error_message=str(e))
    
    async def _handle_replace_existing(self, task: TaskContext) -> TaskResult:
        """Handle replace project request."""
        try:
            # Delete old data
            await self.delete_project_data()
            
            # Get original context
            original_context = task.context.get("original_context", {})
            question_context = original_context.get("question_context", {})
            original_message = (
                question_context.get("original_user_message") or
                original_context.get("original_message") or
                task.content or
                "Tạo project mới"
            )
            original_attachments = (
                question_context.get("attachments") or
                original_context.get("attachments") or
                []
            )
            
            logger.info(f"[ProjectManager] Replacing with {len(original_attachments)} attachment(s)")
            
            # Generate response
            await self.agent.message_user("thinking", "Đang xử lý yêu cầu...")
            
            msg = await generate_response_message(
                action="replace",
                context="User chọn thay thế project cũ",
                extra_info=f"Yêu cầu: {original_message}",
                agent=self.agent
            )
            
            await self.agent.message_user("response", msg, display_mode="chat")
            
            # Delegate to BA
            new_task_context = {}
            if original_attachments:
                new_task_context["attachments"] = original_attachments
            
            conversation_history = self.agent.context.format_memory()
            if conversation_history:
                new_task_context["conversation_history"] = conversation_history
            
            new_task = TaskContext(
                task_id=task.task_id,
                task_type=AgentTaskType.MESSAGE,
                priority="high",
                routing_reason="project_replace_confirmed",
                user_id=task.user_id,
                project_id=self.agent.project_id,
                content=original_message,
                context=new_task_context if new_task_context else None,
            )
            
            await self.agent.delegate_to_role(
                task=new_task,
                target_role="business_analyst",
                delegation_message=msg
            )
            
            return TaskResult(
                success=True,
                output=msg,
                structured_data={"action": "DELEGATE", "target_role": "business_analyst", "replaced": True}
            )
            
        except Exception as e:
            logger.error(f"[ProjectManager] Replace error: {e}", exc_info=True)
            return TaskResult(success=False, output="", error_message=str(e))
    
    async def _handle_keep_existing(self, task: TaskContext) -> TaskResult:
        """Handle keep existing project (no changes)."""
        await self.agent.message_user("thinking", "Đang xử lý...")
        
        msg = await generate_response_message(
            action="keep",
            context="User chọn giữ nguyên project cũ",
            agent=self.agent
        )
        
        await self.agent.message_user("response", msg, display_mode="chat")
        
        return TaskResult(
            success=True,
            output=msg,
            structured_data={"action": "RESPOND", "replaced": False}
        )
    
    async def _handle_new_feature_answer(self, task: TaskContext, answer: str) -> TaskResult:
        """Handle user's answer about what feature to add."""
        try:
            feature_description = (answer or task.content or "").strip()
            
            if not feature_description:
                await self.agent.message_user(
                    "response",
                    "Bạn chưa mô tả feature muốn thêm. Hãy cho mình biết bạn muốn thêm feature gì nhé! 📝"
                )
                return TaskResult(success=False, output="Empty feature description")
            
            # Check cancel intent
            is_cancel = await check_cancel_intent(feature_description, agent=self.agent)
            
            if is_cancel:
                logger.info(f"[ProjectManager] User cancelled: {feature_description}")
                await self.agent.message_user(
                    "response",
                    "OK! Mình sẽ giữ nguyên PRD hiện tại. Nếu cần thêm feature sau, cứ nói với mình nhé! 👍"
                )
                return TaskResult(
                    success=True,
                    output="User cancelled",
                    structured_data={"action": "cancelled"}
                )
            
            logger.info(f"[ProjectManager] User wants to add: {feature_description[:100]}")
            
            # Get context
            original_context = task.context.get("original_context", {})
            question_context = original_context.get("question_context", {})
            existing_title = question_context.get("existing_prd_title", "project hiện tại")
            attachments = question_context.get("attachments", [])
            
            # Generate response
            feature_preview = feature_description[:50] + "..." if len(feature_description) > 50 else feature_description
            msg = f"Đã ghi nhận! 📝 Mình sẽ chuyển cho BA để cập nhật PRD với feature mới: \"{feature_preview}\" nhé!"
            await self.agent.message_user("response", msg)
            
            # Build context
            new_task_context = {
                "is_update_mode": True,
                "existing_prd_title": existing_title,
                "feature_to_add": feature_description,
            }
            if attachments:
                new_task_context["attachments"] = attachments
            
            conversation_history = self.agent.context.format_memory()
            if conversation_history:
                new_task_context["conversation_history"] = conversation_history
            
            # Delegate to BA
            new_task = TaskContext(
                task_id=task.task_id,
                task_type=AgentTaskType.MESSAGE,
                priority="high",
                routing_reason="update_existing_project",
                user_id=task.user_id,
                project_id=self.agent.project_id,
                content=feature_description,
                context=new_task_context
            )
            
            await self.agent.delegate_to_role(
                task=new_task,
                target_role="business_analyst",
                delegation_message=msg
            )
            
            logger.info(f"[ProjectManager] Delegated to BA: {feature_description[:50]}")
            
            return TaskResult(
                success=True,
                output=msg,
                structured_data={"action": "DELEGATE", "target_role": "business_analyst", "update_mode": True}
            )
            
        except Exception as e:
            logger.error(f"[ProjectManager] New feature error: {e}", exc_info=True)
            msg = "Có lỗi xảy ra. Vui lòng thử lại! 😅"
            await self.agent.message_user("response", msg)
            return TaskResult(success=False, output=msg, error_message=str(e))
