"""
Tester/QA Consumer (Debug Mode)

Receives QA/Testing tasks from Team Leader and prints them to console for verification
This is a debug consumer to test the Team Leader orchestration system
"""

import logging
from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from app.crews.events.kafka_consumer import create_consumer
from app.crews.events.event_schemas import KafkaTopics

logger = logging.getLogger(__name__)


class TesterConsumer:
    """
    Tester/QA agent consumer for debugging Team Leader delegation

    Responsibilities:
    - Consume tasks from AGENT_TASKS_TESTER topic
    - Print received testing task information to console
    - Log all task details for debugging orchestration
    """

    def __init__(self):
        self.consumer = None
        self.running = False
        self.task_count = 0

    async def start(self):
        """Start the Tester consumer"""
        try:
            logger.info("=" * 80)
            logger.info("Starting Tester/QA Consumer (Debug Mode)...")
            logger.info("=" * 80)

            # Create consumer for Tester agent tasks
            self.consumer = await create_consumer(
                consumer_id="tester_debug_agent",
                topics=[KafkaTopics.AGENT_TASKS_TESTER],
                group_id="tester_debug_group",
                auto_offset_reset="latest"
            )

            # Register task handler
            self.consumer.register_handler("agent.task", self.handle_task)

            self.running = True
            logger.info("Tester Consumer started - waiting for QA/testing tasks...")
            logger.info("=" * 80)

            # Start consuming
            await self.consumer.consume()

        except Exception as e:
            logger.error(f"Error starting Tester Consumer: {e}")
            raise

    async def stop(self):
        """Stop the Tester consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("Tester Consumer stopped")

    async def handle_task(self, event_data: Dict[str, Any]):
        """
        Handle incoming Tester task from Team Leader

        Event structure:
        {
            "task_id": UUID,
            "agent_type": "tester",
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

            # Print Tester task to console with formatted output
            print("\n" + "=" * 80)
            print(f"🧪 TESTER/QA AGENT - Task #{self.task_count} Received")
            print("=" * 80)
            print(f"🆔 Task ID:          {task_id}")
            print(f"👤 Agent Type:       {agent_type}")
            print(f"📁 Project ID:       {project_id}")
            print(f"💬 Message ID:       {user_message_id}")
            print(f"⏰ Timestamp:        {timestamp}")
            print(f"👔 Delegated By:     {delegated_by}")
            print(f"🎯 Role:             {'PRIMARY Agent' if is_primary else 'Supporting Agent'}")
            print("-" * 80)
            print(f"📝 Task Description (QA Requirements):")
            print(f"   {task_description}")
            print("-" * 80)
            print(f"🧠 Analysis:")
            print(f"   Intent:    {intent}")
            print(f"   Rationale: {rationale}")
            print("-" * 80)
            print(f"🔬 QA/Testing Focus Areas:")
            if "test case" in task_description.lower() or "test plan" in task_description.lower():
                print("   ✓ Test case design")
                print("   ✓ Test plan creation")
                print("   ✓ Test scenario coverage")
            elif "test" in task_description.lower() or "qa" in task_description.lower():
                print("   ✓ Feature testing")
                print("   ✓ Test execution")
                print("   ✓ Quality verification")
            elif "bug" in task_description.lower() or "validate" in task_description.lower():
                print("   ✓ Bug verification")
                print("   ✓ Regression testing")
                print("   ✓ Issue validation")
            else:
                print("   ✓ General QA tasks")
                print("   ✓ Quality assurance")
                print("   ✓ Test coverage analysis")
            print("=" * 80)
            print(f"✅ Tester task logged successfully!")
            print("=" * 80 + "\n")

            # Also log to logger
            logger.info(
                f"Tester Agent received task {task_id} - "
                f"Intent: '{intent}' - "
                f"Description: '{task_description[:100]}...'"
            )
            logger.debug(f"Full Tester task data: {event_data}")

        except Exception as e:
            logger.error(f"Error handling Tester task: {e}", exc_info=True)
            print(f"\n❌ TESTER AGENT ERROR: Failed to process task - {e}\n")


# Global Tester consumer instance
tester_consumer = TesterConsumer()
