"""Story Event Consumer for Tester Agent - Auto-trigger integration test generation."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from app.kafka.consumer import BaseKafkaConsumer
from app.kafka.event_schemas import BaseKafkaEvent, KafkaTopics, RouterTaskEvent, AgentTaskType

logger = logging.getLogger(__name__)

_consumer_instance = None
 

class TesterStoryEventConsumer(BaseKafkaConsumer):
    """Kafka consumer that listens for story status changes to REVIEW and triggers Tester."""
    
    def __init__(self):
        super().__init__(
            topics=["story_events"],
            group_id="tester-story-event-group"
        )
        self.logger = logging.getLogger("TesterConsumer")
    
    async def handle_message(
        self,
        topic: str,
        event: BaseKafkaEvent | Dict[str, Any],
        raw_data: Dict[str, Any],
        key: Optional[str],
        partition: int,
        offset: int,
    ) -> None:
        """Process story event messages and trigger Tester for REVIEW status."""
        try:
            event_type = raw_data.get("event_type")
            
            # Filter for story.status.changed events
            if event_type != "story.status.changed":
                return
            
            # StoryEvent fields are NOT nested in "data" - they're at root level
            new_status = raw_data.get("new_status")
            
            # Only trigger when status changes to REVIEW
            if new_status != "Review":
                return
            
            story_id = raw_data.get("story_id")
            project_id = raw_data.get("project_id")
            
            if not story_id or not project_id:
                self.logger.warning(f"Missing story_id or project_id in event: {raw_data}")
                return
            
            self.logger.info(
                f"[TesterConsumer] Story {story_id} moved to REVIEW status. "
                f"Triggering integration test generation..."
            )
            
            # Query ALL stories in REVIEW status for this project
            # (Batch processing - not just the triggered story)
            from sqlmodel import Session, select
            from app.models import Story, StoryStatus
            from app.core.db import engine
            
            with Session(engine) as session:
                query = select(Story).where(
                    Story.project_id == UUID(project_id),
                    Story.status == StoryStatus.REVIEW
                )
                review_stories = session.exec(query).all()
                story_ids = [str(story.id) for story in review_stories]
            
            if not story_ids:
                self.logger.warning(f"No REVIEW stories found for project {project_id}")
                return
            
            # Find Tester agent in project (like Developer flow)
            from sqlmodel import Session
            from app.services import AgentService
            from app.core.db import engine
            from app.kafka.producer import get_kafka_producer
            
            with Session(engine) as session:
                agent_service = AgentService(session)
                tester = agent_service.get_by_project_and_role(
                    project_id=UUID(project_id),
                    role_type="tester"
                )
            
            if not tester:
                self.logger.warning(f"[TesterConsumer] No Tester agent found in project {project_id}")
                return
            
            self.logger.info(
                f"[TesterConsumer] Found {len(story_ids)} stories in REVIEW. "
                f"Dispatching task to Tester: {tester.human_name} ({tester.id})"
            )
            
            # Dispatch directly to Tester agent using RouterTaskEvent (like Developer)
            producer = await get_kafka_producer()
            
            task_event = RouterTaskEvent(
                event_type="router.task.dispatched",
                task_id=uuid4(),
                task_type=AgentTaskType.WRITE_TESTS,
                agent_id=tester.id,  # UUID - same as Developer
                agent_role="tester",
                source_event_type="story.status.changed",
                source_event_id=str(raw_data.get("event_id", uuid4())),
                routing_reason="story_status_changed_to_review",
                priority="high",
                context={
                    "trigger_type": "status_review",
                    "story_ids": story_ids,
                    "triggered_by_story": story_id,
                    "auto_generated": True,
                    "content": f"Auto-generate integration tests for {len(story_ids)} stories in REVIEW status"
                }
            )
            
            await producer.publish(
                topic=KafkaTopics.AGENT_TASKS,
                event=task_event
            )
            
            self.logger.info(
                f"[TesterConsumer] Task dispatched to {tester.human_name}. "
                f"Generating integration tests for project {project_id}"
            )
            
        except Exception as e:
            self.logger.error(f"[TesterConsumer] Error processing message: {e}", exc_info=True)


async def start_tester_story_consumer():
    """Start the Tester Story Event Consumer."""
    global _consumer_instance
    
    if _consumer_instance is not None:
        logger.warning("TesterStoryEventConsumer already running")
        return
    
    _consumer_instance = TesterStoryEventConsumer()
    await _consumer_instance.start()
    logger.info("✅ TesterStoryEventConsumer started successfully")


async def stop_tester_story_consumer():
    """Stop the Tester Story Event Consumer."""
    global _consumer_instance
    
    if _consumer_instance is None:
        return
    
    await _consumer_instance.stop()
    _consumer_instance = None
    logger.info("TesterStoryEventConsumer stopped")
