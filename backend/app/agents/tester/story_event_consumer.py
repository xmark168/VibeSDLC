"""Story Event Consumer for Tester Agent - Auto-trigger integration test generation."""

import asyncio
import json
import logging
from uuid import UUID
from app.kafka.consumer import BaseConsumer
from app.kafka.topics import KafkaTopics
from app.agents.core.router import RouterTaskEvent, TaskType

logger = logging.getLogger(__name__)

_consumer_instance = None


class TesterStoryEventConsumer(BaseConsumer):
    """Kafka consumer that listens for story status changes to REVIEW and triggers Tester."""
    
    def __init__(self):
        super().__init__(
            consumer_id="tester-story-event-consumer",
            topic=KafkaTopics.STORY_EVENTS,
            group_id="tester-story-event-group"
        )
        self.logger = logging.getLogger("TesterConsumer")
    
    async def process_message(self, message: dict) -> None:
        """Process story event messages and trigger Tester for REVIEW status."""
        try:
            event_type = message.get("event_type")
            
            # Filter for story.status.changed events
            if event_type != "story.status.changed":
                return
            
            data = message.get("data", {})
            new_status = data.get("new_status")
            
            # Only trigger when status changes to REVIEW
            if new_status != "Review":
                return
            
            story_id = data.get("story_id")
            project_id = data.get("project_id")
            
            if not story_id or not project_id:
                self.logger.warning(f"Missing story_id or project_id in event: {message}")
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
                f"Sending task to Tester agent via Router..."
            )
            
            # Send task to Router for Tester agent
            from app.kafka.producer import send_router_task_event
            
            await send_router_task_event(
                RouterTaskEvent(
                    user_id=UUID(data.get("user_id", "00000000-0000-0000-0000-000000000000")),
                    project_id=UUID(project_id),
                    task_type=TaskType.TESTING,
                    content=f"Generate integration tests for {len(story_ids)} stories in REVIEW status",
                    context={
                        "trigger_type": "status_review",
                        "story_ids": story_ids,
                        "triggered_by_story": story_id,
                        "auto_generated": True
                    }
                )
            )
            
            self.logger.info(
                f"[TesterConsumer] Task sent to Router. "
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
