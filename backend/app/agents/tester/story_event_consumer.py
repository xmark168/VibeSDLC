"""Story Event Consumer for Tester Agent - Auto-trigger integration test generation."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from app.kafka.consumer import BaseKafkaConsumer
from app.kafka.event_schemas import BaseKafkaEvent, KafkaTopics, DelegationRequestEvent, AgentTaskType

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
            
            data = raw_data.get("data", {})
            new_status = data.get("new_status")
            
            # Only trigger when status changes to REVIEW
            if new_status != "Review":
                return
            
            story_id = data.get("story_id")
            project_id = data.get("project_id")
            
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
            
            self.logger.info(
                f"[TesterConsumer] Found {len(story_ids)} stories in REVIEW. "
                f"Sending delegation request to Router for Tester agent..."
            )
            
            # Send delegation request to Router (Router will find Tester agent in project)
            from app.kafka.producer import get_kafka_producer
            from uuid import uuid4
            
            producer = await get_kafka_producer()
            
            delegation_event = DelegationRequestEvent(
                event_type="delegation.request",
                event_id=uuid4(),
                project_id=UUID(project_id),
                user_id=UUID(data.get("user_id", "00000000-0000-0000-0000-000000000000")),
                original_task_id=str(uuid4()),
                delegating_agent_id="system",
                delegating_agent_name="TesterStoryConsumer",
                target_role="tester",
                priority="high",
                task_type=AgentTaskType.WRITE_TESTS,
                content=f"Auto-generate integration tests for {len(story_ids)} stories in REVIEW status",
                context={
                    "trigger_type": "status_review",
                    "story_ids": story_ids,
                    "triggered_by_story": story_id,
                    "auto_generated": True
                },
                delegation_message=f"Story {story_id} moved to REVIEW - auto-triggering test generation",
                source_event_type="story.status.changed",
                source_event_id=str(uuid4())
            )
            
            await producer.publish(
                topic=KafkaTopics.DELEGATION_REQUESTS,
                event=delegation_event
            )
            
            self.logger.info(
                f"[TesterConsumer] Delegation request sent to Router. "
                f"Tester will generate integration tests for project {project_id}"
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
