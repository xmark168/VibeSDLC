"""
Business Analyst Consumer (Debug Mode)

Receives BA tasks from Team Leader and prints them to console for verification
This is a debug consumer to test the Team Leader orchestration system
"""

import logging
from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from app.crews.events.kafka_consumer import create_consumer
from app.crews.events.event_schemas import KafkaTopics

logger = logging.getLogger(__name__)


class BusinessAnalystConsumer:
    """
    BA agent consumer for debugging Team Leader delegation

    Responsibilities:
    - Consume tasks from AGENT_TASKS_BA topic
    - Print received BA task information to console
    - Log all task details for debugging orchestration
    """

    def __init__(self):
        self.consumer = None
        self.running = False
        self.task_count = 0

    async def start(self):
        """Start the BA consumer"""
        try:
            logger.info("=" * 80)
            logger.info("Starting Business Analyst Consumer (Debug Mode)...")
            logger.info("=" * 80)

            # Create consumer for BA agent tasks
            self.consumer = await create_consumer(
                consumer_id="ba_debug_agent",
                topics=[KafkaTopics.AGENT_TASKS_BA],
                group_id="ba_debug_group",
                auto_offset_reset="latest"
            )

            # Register task handler
            self.consumer.register_handler("agent.task", self.handle_task)

            self.running = True
            logger.info("BA Consumer started - waiting for story/requirement tasks...")
            logger.info("=" * 80)

            # Start consuming
            await self.consumer.consume()

        except Exception as e:
            logger.error(f"Error starting BA Consumer: {e}")
            raise

    async def stop(self):
        """Stop the BA consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("BA Consumer stopped")

    async def handle_task(self, event_data: Dict[str, Any]):
        """
        Handle incoming BA task from Team Leader

        Event structure:
        {
            "task_id": UUID,
            "agent_type": "ba",
            "project_id": UUID,
            "user_message_id": UUID,
            "task_description": str,
            "context": dict,
            "timestamp": datetime
        }
        """
        try:
            self.task_count += 1

            # Extract task information
            task_id = event_data.get("task_id", "N/A")
            agent_type = event_data.get("agent_type", "N/A")
            project_id = event_data.get("project_id", "N/A")
            user_message_id = event_data.get("user_message_id", "N/A")
            task_description = event_data.get("task_description", "N/A")
            context = event_data.get("context", {})
            timestamp = event_data.get("timestamp", datetime.utcnow())

            # Extract context information
            intent = context.get("intent", "Unknown")
            rationale = context.get("rationale", "No rationale provided")
            is_primary = context.get("is_primary", True)
            delegated_by = context.get("delegated_by", "unknown")

            # Print BA task to console with formatted output
            print("\n" + "=" * 80)
            print(f"📋 BUSINESS ANALYST AGENT - Task #{self.task_count} Received")
            print("=" * 80)
            print(f"🆔 Task ID:          {task_id}")
            print(f"👤 Agent Type:       {agent_type}")
            print(f"📁 Project ID:       {project_id}")
            print(f"💬 Message ID:       {user_message_id}")
            print(f"⏰ Timestamp:        {timestamp}")
            print(f"👔 Delegated By:     {delegated_by}")
            print(f"🎯 Role:             {'PRIMARY Agent' if is_primary else 'Supporting Agent'}")
            print("-" * 80)
            print(f"📝 Task Description (BA Requirements):")
            print(f"   {task_description}")
            print("-" * 80)
            print(f"🧠 Analysis:")
            print(f"   Intent:    {intent}")
            print(f"   Rationale: {rationale}")
            print("-" * 80)
            print(f"💼 BA Focus Areas:")
            if "story" in task_description.lower() or "requirement" in task_description.lower():
                print("   ✓ User story creation")
                print("   ✓ Acceptance criteria definition")
                print("   ✓ Requirements gathering")
            elif "epic" in task_description.lower():
                print("   ✓ Epic breakdown")
                print("   ✓ Feature planning")
            elif "estimate" in task_description.lower() or "points" in task_description.lower():
                print("   ✓ Story point estimation")
                print("   ✓ Effort analysis")
            else:
                print("   ✓ General business analysis")
                print("   ✓ Requirement clarification")
            print("=" * 80)
            print(f"✅ BA task logged successfully!")
            print("=" * 80 + "\n")

            # Also log to logger
            logger.info(
                f"BA Agent received task {task_id} - "
                f"Intent: '{intent}' - "
                f"Description: '{task_description[:100]}...'"
            )
            logger.debug(f"Full BA task data: {event_data}")

        except Exception as e:
            logger.error(f"Error handling BA task: {e}", exc_info=True)
            print(f"\n❌ BA AGENT ERROR: Failed to process task - {e}\n")


# Global BA consumer instance
ba_consumer = BusinessAnalystConsumer()
