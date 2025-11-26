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

    NEW ARCHITECTURE:
    - No more separate Consumer/Role layers
    - Handles tasks via handle_task() method
    - Router sends tasks via @BusinessAnalyst mentions in chat
    - Provides requirements analysis, PRD generation, and business documentation
    """

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
                logger.info(f"[{self.name}] Needs clarification, starting interview...")
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
        """Start interview to gather requirements."""
        # For now, ask a standard question
        # TODO: Use LLM to generate contextual questions
        await self.ask_clarification_question(
            question="Bạn muốn phân tích khía cạnh nào của dự án?",
            question_type="multichoice",
            options=["Requirements", "Architecture", "Risks", "User Stories"],
            allow_multiple=True
        )
        
        state.phase = "interview"
        state.questions_asked.append("Phân tích khía cạnh nào?")
        
        return TaskResult(
            success=True,
            output="⏸️ Đang phỏng vấn...",
            structured_data={"phase": "interview", "waiting": True}
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
    
    async def _handle_resume(self, task: TaskContext) -> TaskResult:
        """Handle resume after user answered clarification question."""
        answer = task.context.get("answer", "")
        selected_options = task.context.get("selected_options", [])
        original_context = task.context.get("original_context", {})
        original_message = original_context.get("original_message", "")
        
        logger.info(
            f"[{self.name}] Resuming with answer: {answer}, "
            f"selected: {selected_options}, original: {original_message}"
        )
        
        # Update conversation state
        state = self._get_conversation_state(task.user_id)
        state.questions_answered.append({
            "question": "Aspects to analyze",
            "answer": answer,
            "selected_options": selected_options
        })
        aspects_details = []
        for aspect in selected_options:
            if aspect == "Requirements":
                aspects_details.append("- Functional and non-functional requirements")
            elif aspect == "Architecture":
                aspects_details.append("- System architecture and design patterns")
            elif aspect == "Risks":
                aspects_details.append("- Technical and business risks")
            elif aspect == "User Stories":
                aspects_details.append("- User stories and acceptance criteria")
        
        # Generate analysis
        response = await self.crew.analyze_with_context(
            original_message=original_message,
            selected_aspects=', '.join(selected_options),
            aspects_list='\n'.join(aspects_details)
        )
        
        logger.info(f"[{self.name}] Resume analysis completed: {len(response)} chars")
        
        # Build PRD data
        prd_data = {
            "project_name": f"Requirements Analysis: {original_message[:50]}",
            "version": "1.0",
            "overview": response[:500] if len(response) > 500 else response,
            "goals": [f"Analyze {aspect}" for aspect in selected_options],
            "target_users": ["Development Team", "Product Owner"],
            "features": [
                {
                    "name": aspect,
                    "description": f"Analysis of {aspect.lower()}"
                }
                for aspect in selected_options
            ],
            "acceptance_criteria": ["Analysis covers all selected aspects"],
            "constraints": [],
            "success_metrics": [],
            "next_steps": ["Review requirements", "Create user stories"],
            "full_analysis": response
        }
        
        # Save PRD to files (if project_files available)
        prd_path = None
        if self.project_files:
            try:
                prd_path = await self.project_files.save_prd(prd_data)
                logger.info(f"[{self.name}] PRD saved to: {prd_path}")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to save PRD file: {e}")
        
        # Create artifact in DB
        try:
            artifact_id = await self.create_artifact(
                artifact_type="prd",
                title=prd_data['project_name'],
                content=prd_data,
                description=f"Requirements analysis: {', '.join(selected_options)}",
                tags=["prd", "requirements", "analysis"] + [asp.lower() for asp in selected_options]
            )
            
            logger.info(f"[{self.name}] Created PRD artifact {artifact_id}")
            
            # Message with file path if available
            file_info = f" **File:** `docs/prd.md`" if prd_path else ""
            
            await self.message_user("response",
                f"📄 Đã tạo Product Requirements Document!{file_info}\n"
                f"**Khía cạnh:** {', '.join(selected_options)}\n\n"
                f"Click vào artifact card bên dưới để xem chi tiết.",
                {
                    "message_type": "artifact_created",
                    "artifact_id": str(artifact_id),
                    "artifact_type": "prd",
                    "title": prd_data['project_name'],
                    "description": f"Requirements analysis: {', '.join(selected_options)}",
                    "version": 1,
                    "status": "draft",
                    "agent_name": self.name
                }
            )
            
            # Clear conversation state
            self._clear_conversation_state(task.user_id)
            
        except Exception as e:
            logger.error(f"[{self.name}] Failed to create artifact: {e}", exc_info=True)
            # Fallback message
            await self.message_user("response", response[:1000], {
                "message_type": "requirements_analysis",
                "data": {"analysis": response, "aspects": selected_options}
            })
        
        return TaskResult(
            success=True,
            output=response,
            structured_data={
                "resumed": True,
                "phase": "prd_created",
                "selected_aspects": selected_options,
                "artifact_id": str(artifact_id) if 'artifact_id' in locals() else None,
                "prd_path": str(prd_path) if prd_path else None
            }
        )
