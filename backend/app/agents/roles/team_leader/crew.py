"""Team Leader Crew - Orchestrator with task assignment authority.

This crew analyzes user messages and delegates to appropriate specialist crews.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from crewai import Agent, Task

from app.agents.roles.base_crew import BaseAgentCrew
from app.agents.roles.team_leader.tasks import create_analyze_and_delegate_task

logger = logging.getLogger(__name__)


class TeamLeaderCrew(BaseAgentCrew):
    """Team Leader Crew - orchestrates task delegation to specialist crews.

    This crew:
    1. Analyzes incoming user messages
    2. Determines which specialist is best suited
    3. Publishes routing events to delegate tasks
    """

    @property
    def crew_name(self) -> str:
        return "Team Leader"

    @property
    def agent_type(self) -> str:
        return "team_leader"

    def _get_default_config_path(self) -> Path:
        """Get default config path for Team Leader."""
        return Path(__file__).parent / "config.yaml"

    def create_agent(self) -> Agent:
        """Create the Team Leader agent.

        Returns:
            Configured CrewAI Agent for team leadership
        """
        agent_config = self.config.get("agent", {})

        self.agent = Agent(
            role=agent_config.get("role", "SDLC Team Leader"),
            goal=agent_config.get(
                "goal",
                "Analyze user requests and delegate tasks to appropriate specialist agents"
            ),
            backstory=agent_config.get(
                "backstory",
                "You are an experienced Team Leader coordinating software development tasks."
            ),
            verbose=agent_config.get("verbose", True),
            allow_delegation=agent_config.get("allow_delegation", True),
            llm=agent_config.get("model", "openai/gpt-4.1"),
        )

        return self.agent

    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create tasks for the Team Leader crew.

        Args:
            context: Context containing user_message

        Returns:
            List of tasks for the crew
        """
        if self.agent is None:
            self.create_agent()

        return [create_analyze_and_delegate_task(self.agent, context)]

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute Team Leader workflow: analyze and delegate.

        This overrides the base execute to handle delegation logic.

        Args:
            context: Context with user_message
            project_id: Optional project ID
            user_id: Optional user ID

        Returns:
            Result with delegation information
        """
        # Execute base workflow
        result = await super().execute(context, project_id, user_id)

        if not result.get("success"):
            return result

        # Parse the delegation decision
        try:
            output = result.get("output", "")

            # Clean up the output (remove markdown code blocks if present)
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()

            # Fix common JSON issues from LLM output
            # First, try to parse as-is
            try:
                delegation_data = json.loads(output)
            except json.JSONDecodeError:
                # Clean up newlines and extra whitespace in string values
                # Replace actual newlines with spaces
                cleaned = output.replace('\n', ' ').replace('\r', ' ')
                # Collapse multiple spaces into one
                cleaned = re.sub(r'\s+', ' ', cleaned)
                delegation_data = json.loads(cleaned)

            specialist = delegation_data.get("specialist", "")
            task_description = delegation_data.get("task_description", "")
            priority = delegation_data.get("priority", "medium")
            delegation_context = delegation_data.get("context", "")
            reasoning = delegation_data.get("reasoning", "")

            # Validate specialist
            valid_specialists = ["business_analyst", "developer", "tester"]
            if specialist not in valid_specialists:
                raise ValueError(f"Invalid specialist: {specialist}")

            # Publish routing event to delegate to specialist
            await self.publish_routing(
                to_agent=specialist,
                delegation_reason=reasoning,
                context={
                    "user_message": context.get("user_message", ""),
                    "task_description": task_description,
                    "priority": priority,
                    "additional_context": delegation_context,
                    "message_id": str(context.get("message_id", "")),
                },
                project_id=project_id,
                user_id=user_id,
            )

            # Update result with delegation info
            result["delegation"] = {
                "specialist": specialist,
                "task_description": task_description,
                "priority": priority,
                "context": delegation_context,
                "reasoning": reasoning,
            }

            # Publish response about delegation
            await self.publish_response(
                content=f"Delegating task to {specialist}: {task_description}",
                message_id=context.get("message_id", UUID(int=0)),
                project_id=project_id,
                user_id=user_id,
                structured_data=result["delegation"],
            )

            logger.info(f"Delegated to {specialist}: {task_description}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse delegation JSON: {e}")
            result["error"] = f"Failed to parse delegation decision: {e}"
            result["success"] = False

        except Exception as e:
            logger.error(f"Delegation failed: {e}", exc_info=True)
            result["error"] = f"Delegation failed: {e}"
            result["success"] = False

        return result
