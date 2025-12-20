
"""Message Router Service - Main router orchestrator."""

import logging
from typing import Any, Dict,Optional

from app.kafka.event_schemas import BaseKafkaEvent, KafkaTopics
from app.kafka.producer import get_kafka_producer
from app.kafka.consumer import BaseKafkaConsumer
from app.agents.routers.user_message_router import UserMessageRouter
from app.agents.routers.agent_message_router import AgentMessageRouter
from app.agents.routers.task_completion_router import TaskCompletionRouter
from app.agents.routers.story_event_router import StoryEventRouter
from app.agents.routers.question_answer_router import QuestionAnswerRouter
from app.agents.routers.batch_answers_router import BatchAnswersRouter
from app.agents.routers.delegation_router import DelegationRouter

logger = logging.getLogger(__name__)

class MessageRouter(BaseKafkaConsumer):
    def __init__(self, seek_to_end: bool = False):
        super().__init__(
            topics=[
                KafkaTopics.USER_MESSAGES.value,
                KafkaTopics.AGENT_EVENTS.value,
                KafkaTopics.STORY_EVENTS.value,
                KafkaTopics.DELEGATION_REQUESTS.value,
                KafkaTopics.QUESTION_ANSWERS.value,
            ],
            group_id="message_router"
        )
        self.seek_to_end = seek_to_end
        self.logger = logging.getLogger(__name__)

    async def start(self, seek_to_end: bool = False) -> None:
        producer = await get_kafka_producer()
        try:
            self.routers = [
                UserMessageRouter(producer),
                AgentMessageRouter(producer),
                TaskCompletionRouter(producer),
                StoryEventRouter(producer),
                QuestionAnswerRouter(producer),
                BatchAnswersRouter(producer),
                DelegationRouter(producer),
            ]

            self.logger.info(f"Initialized {len(self.routers)} routers")

            await super().start(seek_to_end=seek_to_end)

            self.logger.info(f"Message Router Service started successfully (seek_to_end={seek_to_end})")
        except Exception as e:
            self.logger.error(f"Failed to start Message Router: {e}")
            raise

    async def stop(self):
        self.logger.info("Stopping Message Router Service...")
        await super().stop()
        self.logger.info("Message Router Service stopped")
    async def handle_message(
        self,
        topic: str,
        event: BaseKafkaEvent | Dict[str, Any],
        raw_data: Dict[str, Any],
        key: Optional[str],
        partition: int,
        offset: int,
    ) -> None:
        """Handle incoming Kafka message and route to appropriate router."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "unknown")
        self.logger.info(f"📨 Router received: {event_type} from topic {topic}")

        for router in self.routers:
            if router.should_handle(event):
                try:
                    await router.route(event)
                    self.logger.debug(f"Event {event_type} handled by {router.__class__.__name__}")
                    return
                except Exception as e:
                    self.logger.error(
                        f"Error in {router.__class__.__name__} handling {event_type}: {e}",
                        exc_info=True
                    )
                    raise

        self.logger.warning(f"No router handled event type: {event_type}")

_router_service: MessageRouter | None = None

async def get_router_service() -> MessageRouter:
    global _router_service
    if _router_service is None:
        _router_service = MessageRouter()

    return _router_service

async def start_router_service(skip_old_messages: bool = True) -> MessageRouter:
    service = await get_router_service()
    if not hasattr(service, 'running') or not service.running:
        await service.start(seek_to_end=skip_old_messages)
    return service

async def stop_router_service() -> None:
    global _router_service
    if _router_service is not None:
        await _router_service.stop()
        _router_service = None

async def route_story_event(
    story_id: str,
    project_id: str,
    task_type: "AgentTaskType",
    priority: str = "medium",
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Route a story-related event to an available agent.
    """
    from uuid import UUID, uuid4
    from sqlmodel import Session
    from app.core.db import engine
    from app.services.agent_service import AgentService
    from app.models import Story
    from app.kafka.event_schemas import RouterTaskEvent
    from app.kafka.producer import get_kafka_producer
    
    try:
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if not story:
                logger.error(f"[route_story_event] Story not found: {story_id}")
                return False
            
            agent_service = AgentService(session)
            
            developer = agent_service.get_by_project_and_role(
                project_id=UUID(project_id),
                role_type="developer"
            )
            
            if not developer:
                logger.error(f"[route_story_event] No Developer agent for project {project_id}")
                return False
            
            context = {
                "story_id": story_id,
                "project_id": project_id,
                "story_title": story.title,
                "story_description": story.description,
                "pr_url": story.pr_url,
                "worktree_path": story.worktree_path,
                "branch_name": story.branch_name,
                **(metadata or {})
            }
            
            task = RouterTaskEvent(
                task_id=uuid4(),
                task_type=task_type,
                agent_id=developer.id,
                source_event_type="api_trigger",
                source_event_id=str(uuid4()),
                routing_reason=f"route_story_event_{task_type.value}",
                priority=priority,
                project_id=UUID(project_id),
                context=context,
            )
            
            producer = await get_kafka_producer()
            await producer.publish(topic=KafkaTopics.AGENT_TASKS, event=task)
            
            logger.info(f"[route_story_event] Routed {task_type.value} for story {story_id} to {developer.name}")
            return True
            
    except Exception as e:
        logger.error(f"[route_story_event] Error: {e}")
        return False
