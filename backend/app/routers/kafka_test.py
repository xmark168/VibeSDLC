"""Kafka testing router for VibeSDLC"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from app.kafka.producer import kafka_producer
from app.kafka.schemas import AgentTask, AgentTaskType, StoryEvent
from app.dependencies import get_current_active_user
from app.models import User

router = APIRouter(prefix="/kafka", tags=["Kafka Testing"])


@router.post("/test/send-task")
async def send_test_task(
    task_type: AgentTaskType = AgentTaskType.HELLO,
    message: str = "Hello from API!",
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Send a test task to Kafka for agent processing

    This endpoint allows you to send tasks to agents via Kafka.
    """
    try:
        # Create task
        task = AgentTask(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            agent_type="developer",
            payload={"message": message},
            priority=5
        )

        # Send to Kafka
        kafka_producer.send_agent_task(task)
        kafka_producer.flush()

        return {
            "status": "success",
            "message": "Task sent to Kafka successfully",
            "task": task.model_dump(),
            "note": "Check agent logs or consume from 'agent_responses' topic to see the result"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send task: {str(e)}")


@router.post("/test/send-story-event")
async def send_test_story_event(
    story_id: int,
    event_type: str = "status_changed",
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Send a test story event to Kafka

    This simulates a story status change event.
    """
    try:
        # Create story event
        event = StoryEvent(
            event_type=event_type,
            story_id=story_id,
            project_id=1,
            changes={
                "status": {
                    "from": "TODO",
                    "to": "IN_PROGRESS"
                }
            },
            triggered_by=current_user.id,
            timestamp=datetime.utcnow()
        )

        # Send to Kafka
        kafka_producer.send_story_event(event)
        kafka_producer.flush()

        return {
            "status": "success",
            "message": "Story event sent to Kafka successfully",
            "event": event.model_dump()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send story event: {str(e)}")


@router.post("/test/hello-developer")
async def test_hello_developer(
    greeting: str = "Hello, Developer Agent!",
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Send a simple hello task to the developer agent

    This is the simplest way to test the agent integration.
    """
    try:
        task = AgentTask(
            task_id=f"hello_{uuid.uuid4().hex[:8]}",
            task_type=AgentTaskType.HELLO,
            agent_type="developer",
            payload={"message": greeting},
            priority=5
        )

        kafka_producer.send_agent_task(task)
        kafka_producer.flush()

        return {
            "status": "success",
            "message": "Hello task sent to developer agent",
            "task_id": task.task_id,
            "instruction": "The agent will process this task and send a response to the 'agent_responses' topic"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send hello task: {str(e)}")


@router.get("/test/kafka-status")
async def kafka_status() -> Dict[str, Any]:
    """
    Check Kafka connection status
    """
    try:
        from app.kafka.config import kafka_settings
        from app.kafka.producer import kafka_producer

        return {
            "enabled": kafka_settings.KAFKA_ENABLED,
            "bootstrap_servers": kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
            "producer_initialized": kafka_producer._initialized,
            "status": "connected" if kafka_producer._initialized else "disconnected"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
