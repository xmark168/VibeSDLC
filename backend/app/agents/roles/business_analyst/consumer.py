"""Business Analyst Kafka consumer.

Consumes agent routing events and triggers BA crew execution.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import KafkaTopics
from app.agents.roles.business_analyst.crew import BusinessAnalystCrew
from app.models import BASession, BASessionStatus

logger = logging.getLogger(__name__)


class BusinessAnalystConsumer:
    """Kafka consumer for Business Analyst crew.

    Consumes:
    - AgentRoutingEvent from agent.routing topic (where to_agent = "business_analyst")

    Triggers:
    - BusinessAnalystCrew.execute() for each delegation
    - Publishes AgentResponseEvent with analysis results
    """

    def __init__(self, group_id: str = "business-analyst-consumer"):
        """Initialize Business Analyst consumer.

        Args:
            group_id: Kafka consumer group ID
        """
        self.group_id = group_id
        self.engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        self.consumer: Optional[EventHandlerConsumer] = None
        self._running = False

    async def handle_routing_event(self, event_data: Any) -> None:
        """Handle incoming agent routing event.

        Args:
            event_data: Deserialized AgentRoutingEvent data (dict or Pydantic model)
        """
        db_session = None
        try:
            # Convert Pydantic model to dict if needed
            if hasattr(event_data, 'model_dump'):
                event_data = event_data.model_dump(mode='json')

            # Check if this event is for us
            to_agent = event_data.get("to_agent", "")
            if to_agent != "business_analyst":
                logger.debug(f"Routing event not for BA, skipping (to_agent={to_agent})")
                return

            logger.info(f"Business Analyst received delegation from {event_data.get('from_agent')}")

            # Extract context from routing event
            routing_context = event_data.get("context", {})

            # Extract IDs
            project_id = event_data.get("project_id")
            if project_id:
                project_id = UUID(project_id) if isinstance(project_id, str) else project_id

            user_id = event_data.get("user_id")
            if user_id:
                user_id = UUID(user_id) if isinstance(user_id, str) else user_id

            message_id = routing_context.get("message_id")
            if message_id:
                message_id = UUID(message_id) if isinstance(message_id, str) else message_id
            else:
                message_id = uuid4()

            # Create database session
            db_session = Session(self.engine)

            # Create crew with database session
            crew = BusinessAnalystCrew(db_session=db_session)

            # Check for existing active BA session for this project (any active status)
            existing_session = db_session.exec(
                select(BASession)
                .where(BASession.project_id == project_id)
                .where(BASession.status != BASessionStatus.COMPLETED)
                .order_by(BASession.created_at.desc())
            ).first()

            if existing_session:
                # Load existing session
                crew.load_session(existing_session.id)
                logger.info(f"Loaded existing BA session: {existing_session.id}, phase: {existing_session.current_phase}")
            else:
                # Create new session
                crew.create_session(project_id, user_id)
                logger.info(f"Created new BA session: {crew.ba_session.id}")

            # Get user message and current phase
            user_message = routing_context.get("user_message", "")
            current_phase = crew.ba_session.current_phase if crew.ba_session else "analysis"
            user_msg_lower = user_message.lower().strip()

            # Handle message based on current phase
            if current_phase == "analysis":
                # In analysis phase
                if user_msg_lower == "next":
                    logger.info("User requested to proceed to PRD phase")
                    result = await crew.execute_brief_phase(
                        project_id=project_id,
                        user_id=user_id
                    )
                else:
                    # Continue requirements gathering
                    result = await crew.execute_analysis(
                        user_message=user_message,
                        project_id=project_id,
                        user_id=user_id
                    )
            elif current_phase == "brief":
                # In brief phase - waiting for PRD approval/feedback
                if user_msg_lower == "next" or user_msg_lower in ["ok", "approve", "approved", "đồng ý", "chấp nhận"]:
                    logger.info("User approved PRD, proceeding to solution phase")
                    result = await crew.execute_solution_phase(
                        project_id=project_id,
                        user_id=user_id
                    )
                else:
                    # User provided feedback, regenerate PRD
                    logger.info(f"User provided feedback on PRD: {user_message}")
                    result = await crew.execute_brief_phase(
                        revision_feedback=user_message,
                        project_id=project_id,
                        user_id=user_id
                    )
            elif current_phase == "solution":
                # In solution phase - waiting for flows approval/feedback
                if user_msg_lower == "next" or user_msg_lower in ["ok", "approve", "approved", "đồng ý", "chấp nhận"]:
                    logger.info("User approved flows, proceeding to backlog phase")
                    result = await crew.execute_backlog_phase(
                        project_id=project_id,
                        user_id=user_id
                    )
                else:
                    # User provided feedback, regenerate flows
                    logger.info(f"User provided feedback on flows: {user_message}")
                    result = await crew.execute_solution_phase(
                        revision_feedback=user_message,
                        project_id=project_id,
                        user_id=user_id
                    )
            elif current_phase == "backlog":
                # In backlog phase - waiting for backlog approval/feedback
                if user_msg_lower == "next" or user_msg_lower in ["ok", "approve", "approved", "đồng ý", "chấp nhận"]:
                    logger.info("User approved backlog, BA workflow complete")
                    # TODO: Mark session as completed and notify
                    result = {"success": True, "message": "BA workflow completed"}
                else:
                    # User provided feedback, regenerate backlog
                    logger.info(f"User provided feedback on backlog: {user_message}")
                    result = await crew.execute_backlog_phase(
                        revision_feedback=user_message,
                        project_id=project_id,
                        user_id=user_id
                    )
            else:
                # Default to analysis
                result = await crew.execute_analysis(
                    user_message=user_message,
                    project_id=project_id,
                    user_id=user_id
                )

            if result.get("success"):
                logger.info(f"Business Analyst completed task successfully")
            else:
                logger.error(f"Business Analyst execution failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error handling routing event: {e}", exc_info=True)
        finally:
            if db_session:
                db_session.close()

    def _create_consumer(self) -> EventHandlerConsumer:
        """Create and configure the Kafka consumer.

        Returns:
            Configured EventHandlerConsumer
        """
        consumer = EventHandlerConsumer(
            topics=[KafkaTopics.AGENT_ROUTING.value],
            group_id=self.group_id,
        )

        # Register handler for routing events
        consumer.register_handler(
            "agent.routing.delegated",
            lambda event_data: asyncio.create_task(self.handle_routing_event(event_data))
        )

        return consumer

    async def start(self) -> None:
        """Start consuming messages."""
        if self._running:
            logger.warning("Business Analyst consumer already running")
            return

        self.consumer = self._create_consumer()
        self._running = True

        logger.info(f"Starting Business Analyst consumer (group: {self.group_id})")

        # Start consumer (runs consume loop in background)
        await self.consumer.start()

    async def stop(self) -> None:
        """Stop consuming messages."""
        if not self._running:
            return

        self._running = False
        if self.consumer:
            self.consumer.stop()
            self.consumer = None

        logger.info("Business Analyst consumer stopped")

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running
