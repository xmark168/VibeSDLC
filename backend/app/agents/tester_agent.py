"""Tester Agent for VibeSDLC - Validates functionality and ensures quality"""

import logging
import asyncio
import time
from datetime import datetime
from app.kafka.schemas import AgentResponse, AgentTaskStatus, StoryEvent
from app.kafka.producer import kafka_producer
from app.kafka.consumer import KafkaConsumerService
from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class TesterAgent:
    """Tester Agent that processes story status change events"""

    def __init__(self):
        self.agent_id = "tester_001"
        self.agent_type = "TESTER"
        self.consumer = KafkaConsumerService(group_id="tester-consumer-group")
        logger.info(f"Tester agent '{self.agent_id}' initialized")

    async def handle_story_event(self, event_data: dict):
        """Handle incoming story status change event from Kafka"""
        try:
            # Parse story event
            event = StoryEvent(**event_data)

            # Only process status_changed events
            if event.event_type != "status_changed":
                return

            changes = event.changes or {}
            old_status = changes.get("old_status")
            new_status = changes.get("new_status")

            # Tester handles TESTING status
            if new_status != "TESTING":
                return

            logger.info(f"🧪 Tester {self.agent_id} processing story {event.story_id}")
            logger.info(f"   Status: {old_status} → {new_status}")

            start_time = time.time()

            # Simple test logic - just log and respond
            result = self._process_status_change(event, old_status, new_status)

            execution_time = int((time.time() - start_time) * 1000)

            # Send response back to Kafka
            response = AgentResponse(
                task_id=f"story_{event.story_id}_tester",
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentTaskStatus.COMPLETED,
                result=result,
                completed_at=datetime.utcnow(),
                execution_time_ms=execution_time
            )

            kafka_producer.send_agent_response(response)
            logger.info(f"✅ Tester completed processing in {execution_time}ms")

        except Exception as e:
            logger.error(f"❌ Tester error handling event: {e}")
            # Send error response
            response = AgentResponse(
                task_id=f"story_{event_data.get('story_id', 'unknown')}_tester",
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentTaskStatus.FAILED,
                result={},
                error=str(e),
                completed_at=datetime.utcnow()
            )
            kafka_producer.send_agent_response(response)

    def _process_status_change(self, event: StoryEvent, old_status: str, new_status: str) -> dict:
        """Process status change - simple test logic"""

        message = f"Story {event.story_id} is in TESTING. Tester generating test scenarios and validating quality."
        action = "Create test cases from acceptance criteria and perform comprehensive testing"

        # Mock test results
        test_plan = {
            "test_cases_generated": 5,
            "test_scenarios": [
                "Happy path user flow",
                "Edge case handling",
                "Error handling validation",
                "Performance testing",
                "Security validation"
            ],
            "coverage_estimate": "85%",
            "suggested_tests": [
                "Unit tests for business logic",
                "Integration tests for API endpoints",
                "E2E tests for user workflows"
            ]
        }

        return {
            "agent": self.agent_type,
            "story_id": event.story_id,
            "project_id": event.project_id,
            "message": message,
            "action_taken": action,
            "test_plan": test_plan,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def start(self):
        """Start the agent and begin consuming story events"""
        logger.info(f"🚀 Starting Tester agent: {self.agent_id}")

        # Register event handler
        self.consumer.register_handler(
            KafkaTopics.STORY_STATUS_CHANGED,
            self.handle_story_event
        )

        # Initialize consumer
        self.consumer.initialize([KafkaTopics.STORY_STATUS_CHANGED])

        # Start consuming
        await self.consumer.start_consuming()


# Global tester agent instance
tester_agent = TesterAgent()
