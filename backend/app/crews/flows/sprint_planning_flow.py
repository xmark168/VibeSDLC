"""Sprint Planning Flow using CrewAI.

This flow assists with sprint planning by analyzing backlog,
prioritizing stories, and creating sprint plans.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import yaml
from crewai import Agent, Crew, Task
from pydantic import BaseModel

from app.agents.actions.database_actions import DatabaseActions
from app.kafka import (
    AgentResponseEvent,
    FlowStatusEvent,
    FlowStatusType,
    KafkaTopics,
    get_kafka_producer,
)
from app.models import StoryStatus

logger = logging.getLogger(__name__)


class StoryPriority(BaseModel):
    """Story with priority scores."""

    story_id: str
    title: str
    business_value: int  # 1-10
    user_impact: int  # 1-10
    risk_reduction: int  # 1-10
    total_score: int
    justification: str


class SprintPlan(BaseModel):
    """Sprint plan output."""

    sprint_goal: str
    selected_story_ids: List[str]
    assignments: Dict[str, str]  # story_id -> assignee
    capacity_used: int
    risk_mitigation: str


class SprintPlanningFlow:
    """Flow for sprint planning with AI assistance.

    Workflow:
    1. Analyze current backlog
    2. ProductOwner prioritizes stories
    3. TeamLeader creates sprint plan
    4. Return plan for team review
    """

    def __init__(self, db_session, project_id: UUID, user_id: UUID):
        """Initialize flow.

        Args:
            db_session: Database session
            project_id: Project UUID
            user_id: User UUID
        """
        self.db_session = db_session
        self.project_id = project_id
        self.user_id = user_id
        self.db_actions = DatabaseActions(db_session)

        # Load configs
        self.agents_config = self._load_config("agents_config.yaml")
        self.tasks_config = self._load_config("tasks_config.yaml")

        # Initialize agents
        self.team_leader = self._create_agent("team_leader")
        self.product_owner = self._create_agent("product_owner")

        self.flow_id = UUID()

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load YAML config file."""
        import os

        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", filename
        )

        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config {filename}: {e}")
            return {}

    def _create_agent(self, agent_key: str) -> Agent:
        """Create CrewAI agent from config."""
        from crewai import LLM

        config = self.agents_config.get(agent_key, {})
        defaults = self.agents_config.get("defaults", {})

        # Create LLM instance with config
        llm = LLM(
            model=config.get("model", "gpt-4.1"),
            temperature=config.get("temperature", 0.3),
            max_tokens=config.get("max_tokens", 2000),
        )

        return Agent(
            role=config.get("role", agent_key),
            goal=config.get("goal", ""),
            backstory=config.get("backstory", ""),
            verbose=config.get("verbose", True),
            allow_delegation=config.get("allow_delegation", False),
            llm=llm,
            max_iter=defaults.get("max_iter", 15),
            memory=defaults.get("memory", True),
        )

    async def run(
        self,
        team_velocity: int = 40,
        sprint_duration: int = 14,
        business_goals: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run sprint planning flow.

        Args:
            team_velocity: Team's average velocity (story points per sprint)
            sprint_duration: Sprint duration in days
            business_goals: Optional business goals for prioritization

        Returns:
            Sprint plan with prioritized stories
        """
        try:
            # Publish flow started event
            await self._publish_flow_status(
                status=FlowStatusType.STARTED,
                current_step="Analyzing backlog",
            )

            # Step 1: Get backlog stories
            todo_stories = self.db_actions.get_stories_by_project(
                project_id=self.project_id,
                status=StoryStatus.TODO,
            )

            if not todo_stories:
                return {
                    "status": "no_stories",
                    "message": "No stories in backlog",
                }

            # Format stories for analysis
            backlog_data = self._format_stories_for_analysis(todo_stories)

            # Step 2: Analyze backlog
            await self._publish_flow_status(
                status=FlowStatusType.IN_PROGRESS,
                current_step="Analyzing backlog patterns",
                completed_steps=1,
                total_steps=4,
            )

            analyze_task = Task(
                description=self.tasks_config["analyze_backlog"]["description"].format(
                    backlog_stories=backlog_data,
                    team_velocity=team_velocity,
                    sprint_capacity=team_velocity,
                ),
                expected_output=self.tasks_config["analyze_backlog"]["expected_output"],
                agent=self.team_leader,
            )

            analyze_crew = Crew(
                agents=[self.team_leader],
                tasks=[analyze_task],
                verbose=True,
            )

            backlog_analysis = analyze_crew.kickoff()

            # Publish analysis result
            await self._publish_agent_response(
                agent_name="TeamLeader",
                content=str(backlog_analysis),
            )

            # Step 3: Prioritize stories
            await self._publish_flow_status(
                status=FlowStatusType.IN_PROGRESS,
                current_step="Prioritizing stories",
                completed_steps=2,
                total_steps=4,
            )

            prioritize_task = Task(
                description=self.tasks_config["prioritize_stories"]["description"].format(
                    stories=backlog_data,
                    business_goals=business_goals or "Maximize user value and reduce technical debt",
                ),
                expected_output=self.tasks_config["prioritize_stories"]["expected_output"],
                agent=self.product_owner,
            )

            prioritize_crew = Crew(
                agents=[self.product_owner],
                tasks=[prioritize_task],
                verbose=True,
            )

            prioritization = prioritize_crew.kickoff()

            # Publish prioritization result
            await self._publish_agent_response(
                agent_name="ProductOwner",
                content=str(prioritization),
            )

            # Step 4: Create sprint plan
            await self._publish_flow_status(
                status=FlowStatusType.IN_PROGRESS,
                current_step="Creating sprint plan",
                completed_steps=3,
                total_steps=4,
            )

            plan_task = Task(
                description=self.tasks_config["create_sprint_plan"]["description"].format(
                    prioritized_stories=str(prioritization),
                    team_capacity=team_velocity,
                    sprint_duration=sprint_duration,
                ),
                expected_output=self.tasks_config["create_sprint_plan"]["expected_output"],
                agent=self.team_leader,
            )

            plan_crew = Crew(
                agents=[self.team_leader],
                tasks=[plan_task],
                verbose=True,
            )

            sprint_plan = plan_crew.kickoff()

            # Publish sprint plan
            await self._publish_agent_response(
                agent_name="TeamLeader",
                content=str(sprint_plan),
            )

            # Parse and format results
            result = {
                "status": "completed",
                "flow_id": str(self.flow_id),
                "backlog_analysis": str(backlog_analysis)[:500],
                "prioritization": str(prioritization)[:500],
                "sprint_plan": str(sprint_plan),
                "total_stories_analyzed": len(todo_stories),
            }

            # Publish flow completed
            await self._publish_flow_status(
                status=FlowStatusType.COMPLETED,
                completed_steps=4,
                total_steps=4,
                result=result,
            )

            logger.info(f"Sprint planning flow completed: {self.flow_id}")

            return result

        except Exception as e:
            logger.error(f"Sprint planning flow failed: {e}", exc_info=True)

            # Publish flow failed
            await self._publish_flow_status(
                status=FlowStatusType.FAILED,
                error_message=str(e),
            )

            return {
                "status": "failed",
                "error": str(e),
            }

    def _format_stories_for_analysis(self, stories: List) -> str:
        """Format stories for LLM analysis.

        Args:
            stories: List of Story models

        Returns:
            Formatted string of stories
        """
        formatted = []
        for story in stories:
            formatted.append(
                f"- [{story.id}] {story.title}\n"
                f"  Type: {story.type.value}\n"
                f"  Points: {story.story_point or 'Not estimated'}\n"
                f"  Priority: {story.priority or 'Not set'}\n"
                f"  Epic: {story.epic_id or 'None'}\n"
            )

        return "\n".join(formatted)

    # ==================== KAFKA EVENT PUBLISHING ====================

    async def _publish_flow_status(
        self,
        status: FlowStatusType,
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None,
        total_steps: Optional[int] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ):
        """Publish flow status event."""
        try:
            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.FLOW_STATUS,
                event=FlowStatusEvent(
                    project_id=self.project_id,
                    user_id=self.user_id,
                    event_type=status.value,
                    flow_id=self.flow_id,
                    flow_type="sprint_planning",
                    status=status,
                    current_step=current_step,
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    error_message=error_message,
                    result=result,
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish flow status: {e}")

    async def _publish_agent_response(
        self,
        agent_name: str,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
    ):
        """Publish agent response event."""
        try:
            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.AGENT_RESPONSES,
                event=AgentResponseEvent(
                    project_id=self.project_id,
                    user_id=self.user_id,
                    message_id=UUID(),
                    agent_name=agent_name,
                    agent_type=agent_name,
                    content=content,
                    structured_data=structured_data,
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish agent response: {e}")
