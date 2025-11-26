"""Business Analyst Agent - MetaGPT-inspired PRD and User Story management.

NEW ARCHITECTURE:
- File-based PRD management (docs/prd.md + prd.json)
- Multi-turn interview for requirements gathering
- Automatic user story extraction
- Incremental PRD updates
- Responds to @BusinessAnalyst mentions in chat
"""

import asyncio
import logging
from typing import Any, Dict
from uuid import UUID
from pathlib import Path
from dataclasses import dataclass, field

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.business_analyst.crew import BusinessAnalystCrew
from app.models import Agent as AgentModel
from app.utils.project_files import ProjectFiles


logger = logging.getLogger(__name__)


@dataclass
class BAConversationState:
    """Track BA's conversation state with user."""
    conversation_id: UUID
    phase: str = "interview"  # interview, validate, create, edit
    collected_info: dict = field(default_factory=dict)
    questions_asked: list = field(default_factory=list)
    questions_answered: list = field(default_factory=list)
    is_info_complete: bool = False
    existing_prd: dict | None = None
    editing_story_id: UUID | None = None


class BusinessAnalyst(BaseAgent):
    """Business Analyst agent - analyzes requirements and business needs.

    """
    
    # INTERVIEW MODE: "sequential" (adaptive, multi-turn) or "batch" (all questions at once)
    INTERVIEW_MODE = "sequential"  # Default: sequential for adaptive interviews

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Business Analyst."""
        super().__init__(agent_model, **kwargs)

        self.crew = BusinessAnalystCrew()
        
        # Initialize project files manager
        self.project_files = None
        if self.project_id:
            # Get project path from database
            from app.core.db import engine
            from sqlmodel import Session, select
            from app.models import Project
            
            with Session(engine) as session:
                project = session.exec(
                    select(Project).where(Project.id == self.project_id)
                ).first()
                
                if project and project.project_path:
                    self.project_files = ProjectFiles(Path(project.project_path))
                else:
                    # Default path if not set
                    default_path = Path("projects") / str(self.project_id)
                    default_path.mkdir(parents=True, exist_ok=True)
                    self.project_files = ProjectFiles(default_path)
        
        # Conversation state tracking
        self.conversation_states: dict[UUID, BAConversationState] = {}

        logger.info(f"Business Analyst initialized: {self.name}")
    
    def _get_conversation_state(self, user_id: UUID) -> BAConversationState:
        """Get or create conversation state for user."""
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = BAConversationState(
                conversation_id=user_id,
                phase="interview"
            )
        return self.conversation_states[user_id]
    
    def _clear_conversation_state(self, user_id: UUID):
        """Clear conversation state after task completion."""
        if user_id in self.conversation_states:
            del self.conversation_states[user_id]
    
    def _needs_more_clarification(self, state: BAConversationState) -> bool:
        """Check if we need more clarification questions.
        
        Returns True if missing critical info and haven't reached max questions.
        """
        # Max 3 questions in interview
        if len(state.questions_asked) >= 3:
            return False
        
        info = state.collected_info
        
        # Check what's missing
        has_domain = bool(info.get("domain_type"))
        has_users = bool(info.get("user_roles"))
        has_features = bool(info.get("core_features"))
        
        # Need at least domain or features
        if not has_domain and not has_features:
            return True
        
        # If we have domain but no users, ask about users
        if has_domain and not has_users and len(state.questions_asked) < 2:
            return True
        
        # If we have domain and users but no features, ask about features
        if has_domain and has_users and not has_features and len(state.questions_asked) < 3:
            return True
        
        return False

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router."""
        try:
            from app.kafka.event_schemas import AgentTaskType
            
            # Handle resume from clarification question
            if task.task_type == AgentTaskType.RESUME_WITH_ANSWER:
                return await self._handle_resume(task)
            
            user_message = task.content
            logger.info(f"[{self.name}] Processing BA task: {user_message[:50]}...")
            
            # Check if we have project files initialized
            if not self.project_files:
                logger.warning(f"[{self.name}] ProjectFiles not initialized, using simple analysis")
                return await self._simple_analysis(user_message)
            
            # Load existing PRD if available
            existing_prd = await self.project_files.load_prd()
            
            # Get conversation state
            state = self._get_conversation_state(task.user_id)
            if not state.collected_info.get("original_request"):
                state.collected_info["original_request"] = user_message
            state.existing_prd = existing_prd
            
            # Check if we need more information for PRD
            needs_clarification = await self.crew.check_needs_clarification(user_message)
            
            if needs_clarification:
                logger.info(f"[{self.name}] Needs clarification, starting interview (mode={self.INTERVIEW_MODE})...")
                
                # Use configured interview mode
                if self.INTERVIEW_MODE == "batch":
                    return await self._start_interview_batch(state, user_message)
                else:
                    return await self._start_interview(state, user_message)
            
            # Info complete - generate PRD
            logger.info(f"[{self.name}] Info complete, generating PRD...")
            return await self._generate_prd(state, task)

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )
    
    async def _simple_analysis(self, user_message: str) -> TaskResult:
        """Fallback: simple analysis without file management."""
        response = await self.crew.analyze_requirements(user_message)
        
        await self.message_user("response", response, {
            "message_type": "requirements_analysis",
            "data": {"analysis": response}
        })
        
        return TaskResult(
            success=True,
            output=response,
            structured_data={"analysis_type": "simple"}
        )
    
    async def _start_interview(self, state: BAConversationState, user_message: str) -> TaskResult:
        """Start multi-turn interview to gather complete requirements."""
        from datetime import datetime, timezone
        
        # Determine what info is missing
        missing_info = state.collected_info.get("missing_info", [])
        
        # Generate first question using LLM
        question_data = await self.crew.generate_first_clarification_question(
            user_message=user_message,
            missing_info=missing_info
        )
        
        # Ask the question
        await self.ask_clarification_question(
            question=question_data["question_text"],
            question_type=question_data.get("question_type", "multichoice"),
            options=question_data.get("options", []),
            allow_multiple=question_data.get("allow_multiple", False)
        )
        
        state.phase = "interview"
        state.questions_asked.append({
            "question": question_data["question_text"],
            "context": question_data.get("context"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return TaskResult(
            success=True,
            output="⏸️ Đang phỏng vấn...",
            structured_data={"phase": "interview", "waiting": True}
        )
    
    async def _start_interview_batch(self, state: BAConversationState, user_message: str) -> TaskResult:
        """Start batch interview - ask all questions at once for faster UX."""
        from datetime import datetime, timezone
        
        # Determine what info is missing
        missing_info = state.collected_info.get("missing_info", [])
        
        # Generate first question using LLM
        question_data = await self.crew.generate_first_clarification_question(
            user_message=user_message,
            missing_info=missing_info
        )
        
        # Pre-generate additional questions (batch mode = all questions upfront)
        questions_to_ask = [question_data]
        
        # Question 2: User Roles (pre-generated)
        questions_to_ask.append({
            "question_text": "Hệ thống sẽ có những người dùng nào?",
            "question_type": "multichoice",
            "options": [
                "Học sinh/Sinh viên",
                "Giáo viên/Giảng viên",
                "Phụ huynh",
                "Quản trị viên",
                "Other (Khác - vui lòng mô tả)"
            ],
            "allow_multiple": True,
            "context": "user_roles"
        })
        
        # Question 3: Priority (pre-generated)
        questions_to_ask.append({
            "question_text": "Mức độ ưu tiên của dự án này?",
            "question_type": "multichoice",
            "options": [
                "High - Urgent (cần ngay)",
                "Medium - Important (quan trọng)",
                "Low - Nice to have (có thì tốt)"
            ],
            "allow_multiple": False,
            "context": "priority"
        })
        
        # Ask all questions at once
        question_ids = await self.ask_multiple_clarification_questions(questions_to_ask)
        
        state.phase = "interview_batch"
        state.questions_asked = questions_to_ask
        
        logger.info(f"[{self.name}] Asked {len(questions_to_ask)} questions in batch mode")
        
        return TaskResult(
            success=True,
            output=f"⏸️ Đang đợi {len(questions_to_ask)} câu trả lời...",
            structured_data={"phase": "interview_batch", "waiting": True, "batch": True, "question_count": len(questions_to_ask)}
        )
    
    async def _generate_prd(self, state: BAConversationState, task: TaskContext) -> TaskResult:
        """Generate PRD from collected information and save to files."""
        if not self.project_files:
            logger.warning(f"[{self.name}] No ProjectFiles, skipping PRD generation")
            return await self._simple_analysis(state.collected_info.get("original_request", ""))
        
        # Build PRD data
        prd_data = {
            "project_name": f"Project {self.project_id}",  # TODO: Extract from message
            "version": "1.0",
            "overview": f"Requirements for: {state.collected_info.get('original_request', '')}",
            "goals": ["Analyze requirements", "Create user stories"],
            "target_users": ["Development Team"],
            "features": [],
            "acceptance_criteria": [],
            "constraints": [],
            "success_metrics": [],
            "next_steps": ["Review PRD", "Create user stories"]
        }
        
        # Save PRD to files
        prd_path = await self.project_files.save_prd(prd_data)
        logger.info(f"[{self.name}] PRD saved to: {prd_path}")
        
        # Create artifact in DB
        artifact_id = await self.create_artifact(
            artifact_type="prd",
            title=f"PRD: {prd_data['project_name']}",
            content=prd_data,
            description=prd_data['overview'][:200],
            tags=["prd", "requirements"]
        )
        
        # Send message
        await self.message_user("response",
            f"📄 Đã tạo Product Requirements Document!\n"
            f"**File:** `{prd_path.name}`\n\n"
            f"Click vào artifact card bên dưới để xem chi tiết.",
            {
                "message_type": "artifact_created",
                "artifact_id": str(artifact_id),
                "artifact_type": "prd",
                "title": f"PRD: {prd_data['project_name']}",
                "description": prd_data['overview'][:200],
                "version": 1,
                "status": "draft",
                "agent_name": self.name
            }
        )
        
        # Clear conversation state
        self._clear_conversation_state(task.user_id)
        
        return TaskResult(
            success=True,
            output=f"PRD created: {prd_path}",
            structured_data={"phase": "prd_created", "artifact_id": str(artifact_id)}
        )
    
    async def _extract_stories_from_prd(self, prd_data: dict, prd_artifact_id: UUID) -> list[UUID]:
        """Extract user stories from PRD and create in database + file.
        
        Args:
            prd_data: PRD data dictionary
            prd_artifact_id: ID of the PRD artifact
            
        Returns:
            List of created story IDs
        """
        from app.models import Story, StoryType, StoryStatus
        from app.core.db import engine
        from sqlmodel import Session
        from datetime import datetime, timezone
        
        # For now, create simple stories from features
        # TODO: Use LLM to generate detailed user stories
        stories_data = []
        created_story_ids = []
        
        with Session(engine) as session:
            for i, feature in enumerate(prd_data.get('features', []), 1):
                feature_name = feature.get('name', f'Feature {i}') if isinstance(feature, dict) else str(feature)
                feature_desc = feature.get('description', '') if isinstance(feature, dict) else ''
                
                # Create story in DB
                story = Story(
                    project_id=self.project_id,
                    type=StoryType.USER_STORY,
                    title=feature_name,
                    description=f"As a user, I want {feature_name.lower()}, so that I can use this feature.\n\n{feature_desc}",
                    status=StoryStatus.TODO,
                    acceptance_criteria="Given the feature is implemented\nWhen I use it\nThen it works as expected",
                    priority=3,
                    story_points=5,
                    tags=["auto-generated", feature_name.lower().replace(' ', '-')]
                )
                session.add(story)
                session.commit()
                session.refresh(story)
                
                # Collect for file saving
                stories_data.append({
                    "id": f"US-{str(story.id)[:8]}",
                    "title": story.title,
                    "description": story.description,
                    "acceptance_criteria": story.acceptance_criteria,
                    "status": story.status.value,
                    "priority": story.priority,
                    "story_points": story.story_points,
                    "tags": story.tags,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                
                created_story_ids.append(story.id)
        
        # Save ALL stories to ONE file
        if self.project_files and stories_data:
            try:
                stories_path = await self.project_files.save_user_stories(stories_data)
                logger.info(f"[{self.name}] Saved {len(stories_data)} stories to: {stories_path}")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to save stories file: {e}")
        
        # Send summary message
        if created_story_ids:
            await self.message_user("response",
                f"✅ Đã tạo {len(created_story_ids)} User Stories!\n\n"
                f"Stories này đã được thêm vào backlog (TODO).\n"
                f"TeamLeader sẽ assign cho developers sau.",
                {
                    "message_type": "stories_created",
                    "story_ids": [str(sid) for sid in created_story_ids],
                    "prd_artifact_id": str(prd_artifact_id),
                    "count": len(created_story_ids)
                }
            )
        
        return created_story_ids
    
    async def _generate_prd_from_interview(self, state: BAConversationState, task: TaskContext) -> TaskResult:
        """Generate PRD from completed interview data."""
        from datetime import datetime, timezone
        
        # Build comprehensive PRD from collected info
        collected = state.collected_info
        
        # Use LLM to generate proper PRD (future enhancement)
        # For now, use collected data directly
        domain_type = collected.get("domain_type", ["General System"])[0] if isinstance(collected.get("domain_type"), list) else collected.get("domain_type", "General System")
        user_roles = collected.get("user_roles", ["End Users"])
        features = collected.get("core_features", ["Core functionality"])
        
        prd_data = {
            "project_name": f"{domain_type} System",
            "version": "1.0",
            "overview": f"System type: {domain_type}. Target users: {', '.join(user_roles)}. Core features: {', '.join(features)}",
            "goals": [f"Implement {feature}" for feature in features[:3]],
            "target_users": user_roles,
            "features": [{"name": f, "description": f"Implementation of {f}"} for f in features],
            "acceptance_criteria": ["System meets all specified requirements"],
            "constraints": [],
            "success_metrics": ["User satisfaction", "System performance"],
            "next_steps": ["Review PRD", "Create user stories", "Begin development"]
        }
        
        if not self.project_files:
            # Fallback without files
            await self.message_user("response",
                f"✅ Cảm ơn! Đã thu thập đủ thông tin.\n\n"
                f"**Loại hệ thống:** {domain_type}\n"
                f"**Người dùng:** {', '.join(user_roles)}\n"
                f"**Tính năng:** {', '.join(features)}",
                {"message_type": "interview_complete"}
            )
            self._clear_conversation_state(task.user_id)
            return TaskResult(success=True, output="Interview complete")
        
        # Save PRD to files
        prd_path = await self.project_files.save_prd(prd_data)
        logger.info(f"[{self.name}] PRD saved to: {prd_path}")
        
        # Create artifact
        artifact_id = await self.create_artifact(
            artifact_type="prd",
            title=f"PRD: {prd_data['project_name']}",
            content=prd_data,
            description=prd_data['overview'][:200],
            tags=["prd", "interview", domain_type.lower().replace(' ', '-')]
        )
        
        logger.info(f"[{self.name}] Created PRD artifact {artifact_id}")
        
        # Send message
        await self.message_user("response",
            f"✅ Cảm ơn! Tôi đã thu thập đủ thông tin.\n\n"
            f"📄 Đang tạo Product Requirements Document...\n"
            f"**File:** `{prd_path.name}`",
            {
                "message_type": "artifact_created",
                "artifact_id": str(artifact_id),
                "artifact_type": "prd",
                "title": f"PRD: {prd_data['project_name']}",
                "description": prd_data['overview'][:200],
                "version": 1,
                "status": "draft",
                "agent_name": self.name
            }
        )
        
        # Clear conversation state
        self._clear_conversation_state(task.user_id)
        
        return TaskResult(
            success=True,
            output=f"PRD created: {prd_path}",
            structured_data={"phase": "prd_created", "artifact_id": str(artifact_id)}
        )
    
    async def _handle_resume_batch(self, task: TaskContext, batch_answers: list[dict]) -> TaskResult:
        """Handle resume after user answered batch questions."""
        from datetime import datetime, timezone
        
        # Get conversation state
        state = self._get_conversation_state(task.user_id)
        
        # Store all answers
        for ans_data in batch_answers:
            answer = ans_data.get("answer", "")
            selected_options = ans_data.get("selected_options", [])
            
            state.questions_answered.append({
                "question_id": ans_data.get("question_id"),
                "answer": answer,
                "selected_options": selected_options,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Update collected_info from all answers
        for idx, ans_data in enumerate(batch_answers):
            selected_options = ans_data.get("selected_options", [])
            answer = ans_data.get("answer", "")
            
            # Map to context (based on batch order)
            if idx < len(state.questions_asked):
                question_context = state.questions_asked[idx].get("context") if isinstance(state.questions_asked[idx], dict) else None
                
                if question_context == "domain":
                    state.collected_info["domain_type"] = selected_options if selected_options else [answer]
                elif question_context == "user_roles":
                    state.collected_info["user_roles"] = selected_options if selected_options else [answer]
                elif question_context == "priority":
                    state.collected_info["priority"] = selected_options[0] if selected_options else answer
                else:
                    # Fallback
                    state.collected_info[f"answer_{idx}"] = selected_options if selected_options else [answer]
        
        # All batch questions answered - generate PRD
        logger.info(f"[{self.name}] All {len(batch_answers)} batch answers received. Generating PRD...")
        state.is_info_complete = True
        
        return await self._generate_prd_from_interview(state, task)
    
    async def _handle_resume(self, task: TaskContext) -> TaskResult:
        """Handle resume after user answered clarification question (multi-turn or batch)."""
        from datetime import datetime, timezone
        
        # Check if batch mode
        is_batch = task.context.get("is_batch", False)
        batch_answers = task.context.get("batch_answers", [])
        
        if is_batch:
            logger.info(f"[{self.name}] Resuming with BATCH answers ({len(batch_answers)} questions)")
            return await self._handle_resume_batch(task, batch_answers)
        
        # Single answer mode (sequential)
        answer = task.context.get("answer", "")
        selected_options = task.context.get("selected_options", [])
        
        logger.info(
            f"[{self.name}] Resuming with answer: {answer}, "
            f"selected: {selected_options}"
        )
        
        # Get conversation state
        state = self._get_conversation_state(task.user_id)
        
        # Store answer
        state.questions_answered.append({
            "question": state.questions_asked[-1] if state.questions_asked else {},
            "answer": answer,
            "selected_options": selected_options,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Update collected_info based on last question context
        if state.questions_asked:
            last_question_context = state.questions_asked[-1].get("context") if isinstance(state.questions_asked[-1], dict) else None
            
            if last_question_context == "domain":
                state.collected_info["domain_type"] = selected_options if selected_options else [answer]
            elif last_question_context == "user_roles":
                state.collected_info["user_roles"] = selected_options if selected_options else [answer]
            elif last_question_context == "features":
                state.collected_info["core_features"] = selected_options if selected_options else [answer]
            else:
                # Fallback for old-style questions (aspects)
                state.collected_info["aspects"] = selected_options if selected_options else [answer]
        
        # Check if need more questions
        needs_more = self._needs_more_clarification(state)
        
        if needs_more and len(state.questions_asked) < 3:
            # Generate next question
            logger.info(f"[{self.name}] Need more info, asking next question...")
            
            try:
                next_question = await self.crew.generate_next_interview_question(
                    user_message=state.collected_info.get("original_request", ""),
                    collected_info=state.collected_info,
                    previous_questions=state.questions_asked
                )
                
                await self.ask_clarification_question(
                    question=next_question["question_text"],
                    question_type=next_question.get("question_type", "multichoice"),
                    options=next_question.get("options", []),
                    allow_multiple=next_question.get("allow_multiple", False)
                )
                
                state.questions_asked.append({
                    "question": next_question["question_text"],
                    "context": next_question.get("context"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                return TaskResult(
                    success=True,
                    output="⏸️ Tiếp tục phỏng vấn...",
                    structured_data={"phase": "interview", "waiting": True}
                )
            except Exception as e:
                logger.error(f"[{self.name}] Failed to generate next question: {e}")
                # Continue to PRD generation
        
        # Info complete → Generate PRD
        logger.info(f"[{self.name}] Interview complete, generating PRD...")
        state.is_info_complete = True
        return await self._generate_prd_from_interview(state, task)
