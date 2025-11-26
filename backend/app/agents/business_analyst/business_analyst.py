"""
Business Analyst Agent

ARCHITECTURE NOTE:
Uses AgentToolContext for dependency injection, allowing tools to access
agent operations without tight coupling to pool manager.
"""

import json
import logging
from uuid import UUID
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.agent_context import AgentToolContext
from app.agents.business_analyst.crew import BusinessAnalystCrew
from app.models import Agent as AgentModel
from app.utils.project_files import ProjectFiles
from app.kafka.event_schemas import AgentTaskType

logger = logging.getLogger(__name__)


@dataclass
class BAConversationState:
    conversation_id: UUID
    intent: str = "unknown"
    phase: str = "initial"
    collected_info: dict = field(default_factory=dict)
    questions_asked: list = field(default_factory=list)
    questions_answered: list = field(default_factory=list)
    is_info_complete: bool = False
    existing_prd: dict | None = None
    editing_story_id: UUID | None = None


class BusinessAnalyst(BaseAgent):
    """Business Analyst agent.
    
    INTERVIEW_MODE: "sequential" (adaptive) or "batch" (all questions at once).
    """
    
    INTERVIEW_MODE = "sequential"

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)

        # Create tool context for dependency injection
        tool_context = AgentToolContext(self)
        
        self.crew = BusinessAnalystCrew(
            agent_name=agent_model.human_name,
            personality_traits=agent_model.personality_traits or [],
            communication_style=agent_model.communication_style,
            tool_context=tool_context  # Inject context into crew
        )
        
        self.project_files = None
        if self.project_id:
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
                    default_path = Path("projects") / str(self.project_id)
                    default_path.mkdir(parents=True, exist_ok=True)
                    self.project_files = ProjectFiles(default_path)
        
        self.conversation_states: dict[UUID, BAConversationState] = {}

        logger.info(f"Business Analyst initialized: {self.name}")
    
    def _get_conversation_state(self, user_id: UUID) -> BAConversationState:
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = BAConversationState(
                conversation_id=user_id,
                phase="interview"
            )
        return self.conversation_states[user_id]
    
    def _clear_conversation_state(self, user_id: UUID):
        if user_id in self.conversation_states:
            del self.conversation_states[user_id]

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using CrewAI Hierarchical Process."""
        try:
            # Handle resume - delegate to crew with collected info
            if task.task_type == AgentTaskType.RESUME_WITH_ANSWER:
                return await self._resume_with_crew(task)
            
            user_message = task.content
            logger.info(f"[{self.name}] Processing with Hierarchical Crew: {user_message[:80]}...")
            
            # Check if we have project files initialized
            if not self.project_files:
                logger.warning(f"[{self.name}] No ProjectFiles, using simple analysis")
                return await self._simple_analysis(user_message)
            
            # Prepare inputs for hierarchical crew
            inputs = {
                "user_message": user_message,
                "existing_prd": "None",
                "collected_info": "{}",
                "context": "",
                "agent_id": str(self.agent_id),  # For ask_user_question tool
                "agent_name": self.name
            }
            
            # Load existing PRD if available
            try:
                existing_prd = await self.project_files.load_prd()
                if existing_prd:
                    inputs["existing_prd"] = json.dumps(existing_prd, ensure_ascii=False, indent=2)
                    logger.info(f"[{self.name}] Loaded existing PRD")
            except Exception as e:
                logger.debug(f"[{self.name}] No existing PRD: {e}")
            
            # Get conversation state for context
            conv_state = self._get_conversation_state(task.user_id)
            if conv_state.collected_info:
                inputs["collected_info"] = json.dumps(conv_state.collected_info, ensure_ascii=False, indent=2)
            
            # Run hierarchical crew - manager will delegate to team
            logger.info(f"[{self.name}] Running hierarchical crew...")
            result = await self.crew.crew().kickoff_async(inputs=inputs)
            
            # Parse JSON result from manager
            result_data = self._parse_crew_result(str(result))
            action = result_data.get("action_taken", "unknown")
            output = result_data.get("result", {})
            summary = result_data.get("summary", "")
            next_steps = result_data.get("next_steps", [])
            
            logger.info(f"[{self.name}] Crew completed: action={action}")
            
            # Send appropriate response to user based on action
            await self._send_result_to_user(action, output, summary, next_steps)
            
            # Save artifacts if needed
            if action == "generated_prd" or action == "updated_prd":
                if self.project_files and isinstance(output, dict):
                    await self.project_files.save_prd(output)
                    logger.info(f"[{self.name}] PRD saved")
            
            # Update conversation state
            conv_state.phase = action
            if isinstance(output, dict) and "collected_info" in output:
                conv_state.collected_info.update(output["collected_info"])
            
            return TaskResult(
                success=True,
                output=str(result),
                structured_data=result_data
            )

        except Exception as e:
            logger.error(f"[{self.name}] Crew error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )
    
    def _parse_crew_result(self, result_str: str) -> dict:
        """Parse JSON result from crew with fallback."""
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            return json.loads(result_str)
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.warning(f"[{self.name}] Could not parse crew result as JSON: {e}")
            return {
                "action_taken": "unknown",
                "result": result_str,
                "summary": "Crew completed but result format unexpected",
                "next_steps": []
            }
    
    async def _send_result_to_user(self, action: str, output: any, summary: str, next_steps: list):
        """Send appropriate message to user based on action type."""
        if action == "interviewed":
            # Questions generated - ask user
            questions = output.get("questions", []) if isinstance(output, dict) else []
            if questions:
                await self.message_user("clarification_question",
                    f"**Câu hỏi làm rõ:**\n\n{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(questions))}\n\n{summary}",
                    {"questions": questions, "next_steps": next_steps}
                )
            else:
                await self.message_user("response", summary, {"next_steps": next_steps})
        
        elif action == "generated_prd":
            await self.message_user("response",
                f"✅ **PRD Created Successfully**\n\n{summary}\n\n**Next steps:**\n" +
                "\n".join(f"- {step}" for step in next_steps),
                {"prd": output, "next_steps": next_steps}
            )
        
        elif action == "updated_prd":
            change_summary = output.get("change_summary", "PRD updated") if isinstance(output, dict) else "PRD updated"
            await self.message_user("response",
                f"✅ **PRD Updated**\n\n{change_summary}\n\n{summary}",
                {"prd": output, "next_steps": next_steps}
            )
        
        elif action == "extracted_stories":
            stories_count = len(output) if isinstance(output, list) else 0
            await self.message_user("response",
                f"✅ **User Stories Extracted** ({stories_count} stories)\n\n{summary}\n\n**Next steps:**\n" +
                "\n".join(f"- {step}" for step in next_steps),
                {"stories": output, "next_steps": next_steps}
            )
        
        elif action == "domain_analysis":
            analysis_text = output.get("analysis_text", str(output)) if isinstance(output, dict) else str(output)
            await self.message_user("response",
                f"📊 **Domain Analysis Complete**\n\n{analysis_text}\n\n{summary}",
                {"analysis": output, "next_steps": next_steps}
            )
        
        else:
            # Unknown action - send raw result
            await self.message_user("response", f"{summary}\n\nResult: {str(output)[:500]}")
    
    async def _simple_analysis(self, user_message: str) -> TaskResult:
        """Fallback: simple analysis without file management."""
        try:
            # Run crew with minimal inputs
            result = await self.crew.crew().kickoff_async(inputs={
                "user_message": user_message,
                "existing_prd": "None",
                "collected_info": "{}",
                "context": "",
                "agent_id": str(self.agent_id),
                "agent_name": self.name
            })
            
            result_str = str(result)
            await self.message_user("response", result_str[:1000], {
                "message_type": "requirements_analysis"
            })
            
            return TaskResult(
                success=True,
                output=result_str,
                structured_data={"analysis_type": "simple"}
            )
        except Exception as e:
            logger.error(f"[{self.name}] Simple analysis error: {e}")
            return TaskResult(
                success=False,
                output="",
                error_message=str(e)
            )
    
    async def _resume_with_crew(self, task: TaskContext) -> TaskResult:
        """Resume workflow by delegating to crew with collected info."""
        try:
            # Get conversation state
            conv_state = self._get_conversation_state(task.user_id)
            
            # Add user's answer to collected info
            user_answer = task.content
            conv_state.questions_asked.append({
                "answer": user_answer,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"[{self.name}] Resume with user answer: {user_answer[:80]}...")
            
            # Prepare inputs with collected info
            inputs = {
                "user_message": f"User provided answer: {user_answer}. Continue BA workflow based on collected information.",
                "existing_prd": "None",
                "collected_info": json.dumps(conv_state.collected_info, ensure_ascii=False, indent=2),
                "context": "",
                "agent_id": str(self.agent_id),
                "agent_name": self.name
            }
            
            # Load existing PRD if available
            if self.project_files:
                try:
                    existing_prd = await self.project_files.load_prd()
                    if existing_prd:
                        inputs["existing_prd"] = json.dumps(existing_prd, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.warning(f"[{self.name}] Could not load existing PRD: {e}")
            
            # Resume crew task
            logger.info(f"[{self.name}] Resuming crew with collected info...")
            result = await self.crew.crew().kickoff_async(inputs=inputs)
            
            # Parse and send result
            result_data = self._parse_crew_result(str(result))
            action = result_data.get("action_taken", "unknown")
            output = result_data.get("result", {})
            summary = result_data.get("summary", "")
            next_steps = result_data.get("next_steps", [])
            
            await self._send_result_to_user(action, output, summary, next_steps)
            
            # Save artifacts if needed
            if action in ["generated_prd", "updated_prd"]:
                if self.project_files and isinstance(output, dict):
                    try:
                        await self.project_files.save_prd(output)
                        
                        # Create artifact
                        artifact_id = await self.create_artifact(
                            artifact_type="prd",
                            title=f"PRD: {output.get('project_name', 'Project')}",
                            content=output,
                            description=output.get('overview', '')[:200],
                            tags=["prd", "business_analysis"]
                        )
                        logger.info(f"[{self.name}] Created PRD artifact {artifact_id}")
                    except Exception as e:
                        logger.error(f"[{self.name}] Failed to save PRD: {e}")
            
            # Update state
            conv_state.phase = action
            
            # Clear state if complete
            if action in ["generated_prd", "updated_prd", "extracted_stories"]:
                self._clear_conversation_state(task.user_id)
            
            return TaskResult(
                success=True,
                output=str(result),
                structured_data=result_data
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Resume error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e)
            )
