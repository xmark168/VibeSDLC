"""Story Generation Flow using CrewAI.

This flow orchestrates the creation of user stories from user messages,
with human-in-the-loop approval before creating stories in the database.
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

import yaml
from crewai import Agent, Crew, Task
from pydantic import BaseModel

from app.agents.actions.database_actions import DatabaseActions
from app.kafka import (
    AgentResponseEvent,
    AgentRoutingEvent,
    ApprovalRequestEvent,
    KafkaTopics,
    StoryCreatedEvent,
    get_kafka_producer,
)
from app.models import ApprovalStatus, StoryStatus, StoryType

logger = logging.getLogger(__name__)


class StoryProposal(BaseModel):
    """Proposed story from BA agent."""

    title: str
    description: str
    acceptance_criteria: str
    story_point: int
    story_type: str = "UserStory"
    priority: int = 1


class StoryGenerationFlow:
    """Flow for generating user stories from user messages.

    Workflow:
    1. TeamLeader analyzes user message
    2. BA creates story proposal
    3. Send approval request to user
    4. On approval, create story in database
    5. Publish events via Kafka
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
        self.business_analyst = self._create_agent("business_analyst")

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load YAML config file.

        Args:
            filename: Config filename

        Returns:
            Parsed YAML config
        """
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
        """Create CrewAI agent from config.

        Args:
            agent_key: Agent key in config

        Returns:
            CrewAI Agent instance
        """
        from crewai import LLM

        config = self.agents_config.get(agent_key, {})
        defaults = self.agents_config.get("defaults", {})

        # Create LLM instance with config
        llm = LLM(
            model=config.get("model", "openai/gpt-4.1"),
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
        user_message: str,
        execution_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Run the story generation flow.

        Args:
            user_message: User's message/requirement
            execution_id: Optional agent execution ID for tracking

        Returns:
            Flow result with approval_request_id
        """
        try:
            # Publish routing event
            await self._publish_routing_event(
                from_agent="System",
                to_agent="TeamLeader",
                reason="Analyzing user message for story creation",
            )

            # Step 1: TeamLeader analyzes message
            analysis_task = Task(
                description=self.tasks_config["analyze_user_message"]["description"].format(
                    user_message=user_message
                ),
                expected_output=self.tasks_config["analyze_user_message"]["expected_output"],
                agent=self.team_leader,
            )

            analysis_crew = Crew(
                agents=[self.team_leader],
                tasks=[analysis_task],
                verbose=True,
            )

            analysis_result = analysis_crew.kickoff()

            # Publish agent response
            await self._publish_agent_response(
                agent_name="TeamLeader",
                content=str(analysis_result),
                execution_id=execution_id,
            )

            # Publish routing to BA
            await self._publish_routing_event(
                from_agent="TeamLeader",
                to_agent="BusinessAnalyst",
                reason="Creating user story from requirements",
            )

            # Step 2: BA creates story
            project = self.db_actions.get_project(self.project_id)
            tech_stack = project.tech_stack if project else "unknown"

            story_task = Task(
                description=self.tasks_config["create_user_story"]["description"].format(
                    requirements=str(analysis_result),
                    project_context=f"Tech stack: {tech_stack}",
                ),
                expected_output=self.tasks_config["create_user_story"]["expected_output"],
                agent=self.business_analyst,
                output_json=StoryProposal,
            )

            story_crew = Crew(
                agents=[self.business_analyst],
                tasks=[story_task],
                verbose=True,
            )

            story_result = story_crew.kickoff()

            # Parse story proposal
            story_data = self._parse_story_result(story_result)

            # Publish agent response
            await self._publish_agent_response(
                agent_name="BusinessAnalyst",
                content=f"Created story proposal: {story_data['title']}",
                structured_data=story_data,
                execution_id=execution_id,
            )

            # Step 3: Create approval request
            approval_request = self.db_actions.create_approval_request(
                project_id=self.project_id,
                request_type="story_creation",
                agent_name="BusinessAnalyst",
                proposed_data=story_data,
                preview_data={
                    "title": story_data["title"],
                    "description": story_data["description"][:200] + "..."
                    if len(story_data.get("description", "")) > 200
                    else story_data.get("description", ""),
                },
                explanation=f"Proposed user story based on: {user_message[:100]}...",
                execution_id=execution_id,
            )

            # Publish approval request event
            await self._publish_approval_request(approval_request.id, story_data)

            logger.info(
                f"Story generation flow completed - approval request: {approval_request.id}"
            )

            return {
                "status": "pending_approval",
                "approval_request_id": str(approval_request.id),
                "story_preview": story_data,
            }

        except Exception as e:
            logger.error(f"Story generation flow failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    def _parse_story_result(self, result: Any) -> Dict[str, Any]:
        """Parse story result from CrewAI.

        Args:
            result: CrewAI task result

        Returns:
            Story data dictionary
        """
        import json
        import re

        result_str = str(result)

        # Try to extract JSON
        json_match = re.search(r'\{[\s\S]*\}', result_str)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback: manual parsing
        return {
            "title": "User Story",
            "description": result_str[:500],
            "acceptance_criteria": "To be defined",
            "story_point": 5,
            "story_type": "UserStory",
            "priority": 1,
        }

    async def apply_approval(
        self,
        approval_id: UUID,
        user_feedback: Optional[str] = None,
        modified_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Apply approved story creation.

        Args:
            approval_id: Approval request ID
            user_feedback: Optional user feedback
            modified_data: Optional user modifications to story

        Returns:
            Result with created story ID
        """
        try:
            # Get approval request
            approval = self.db_session.get(self.db_actions.ApprovalRequest, approval_id)
            if not approval or approval.status != ApprovalStatus.APPROVED:
                return {"status": "error", "message": "Approval not found or not approved"}

            # Use modified data if provided, otherwise use proposed data
            story_data = modified_data or approval.proposed_data

            # Create story in database
            story = self.db_actions.create_story(
                project_id=self.project_id,
                title=story_data["title"],
                description=story_data.get("description"),
                story_type=StoryType(story_data.get("story_type", "UserStory")),
                status=StoryStatus.TODO,
                acceptance_criteria=story_data.get("acceptance_criteria"),
                story_point=story_data.get("story_point"),
                priority=story_data.get("priority"),
                created_by_agent="BusinessAnalyst",
            )

            # Mark approval as applied
            self.db_actions.mark_approval_applied(
                approval_id=approval_id,
                created_entity_id=story.id,
            )

            # Publish story created event
            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.STORY_EVENTS,
                event=StoryCreatedEvent(
                    project_id=self.project_id,
                    user_id=self.user_id,
                    story_id=story.id,
                    title=story.title,
                    description=story.description,
                    story_type=story.type.value,
                    status=story.status.value,
                    created_by_agent="BusinessAnalyst",
                ),
            )

            logger.info(f"Created story {story.id} from approval {approval_id}")

            return {
                "status": "success",
                "story_id": str(story.id),
                "story": {
                    "id": str(story.id),
                    "title": story.title,
                    "status": story.status.value,
                },
            }

        except Exception as e:
            logger.error(f"Failed to apply approval: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    # ==================== KAFKA EVENT PUBLISHING ====================

    async def _publish_routing_event(
        self, from_agent: str, to_agent: str, reason: str
    ):
        """Publish agent routing event."""
        try:
            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.AGENT_ROUTING,
                event=AgentRoutingEvent(
                    project_id=self.project_id,
                    user_id=self.user_id,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    delegation_reason=reason,
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish routing event: {e}")

    async def _publish_agent_response(
        self,
        agent_name: str,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
        execution_id: Optional[UUID] = None,
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

    async def _publish_approval_request(
        self, approval_id: UUID, story_data: Dict[str, Any]
    ):
        """Publish approval request event."""
        try:
            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.APPROVAL_REQUESTS,
                event=ApprovalRequestEvent(
                    project_id=self.project_id,
                    user_id=self.user_id,
                    approval_request_id=approval_id,
                    request_type="story_creation",
                    agent_name="BusinessAnalyst",
                    proposed_data=story_data,
                    preview_data={
                        "title": story_data["title"],
                        "description": story_data.get("description", "")[:200],
                    },
                    explanation="Proposed user story for approval",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish approval request: {e}")
