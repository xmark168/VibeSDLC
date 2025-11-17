"""
Router Agent Consumer

Analyzes user messages and routes them to appropriate specialist agents
Supports both AI-based routing and explicit @mention routing
"""

import asyncio
import logging
import re
import uuid
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.crews.events.kafka_consumer import create_consumer
from app.crews.events.kafka_producer import get_kafka_producer
from app.crews.events.event_schemas import (
    KafkaTopics,
    AgentTaskEvent,
    AgentRoutingEvent,
)

logger = logging.getLogger(__name__)


class RouterAgent:
    """
    Routes user messages to appropriate specialist agents

    Routing strategies:
    1. Explicit @mention: @ba, @dev, @tester, @leader
    2. Keyword detection: story, bug, test, metrics, etc.
    3. AI classification (future enhancement)
    """

    def __init__(self):
        self.consumer = None
        self.producer = None
        self.running = False

        # Mention patterns
        self.mention_pattern = re.compile(r'@(ba|dev|developer|tester|test|leader|pm)')

        # Keyword mappings
        self.keywords = {
            "ba": [
                "create story", "user story", "acceptance criteria", "epic",
                "requirement", "refine story", "story points", "estimate",
                "feature description", "business requirement", "user need"
            ],
            "dev": [
                "code", "implement", "bug", "error", "debug", "function",
                "class", "api", "endpoint", "database", "fix", "technical"
            ],
            "tester": [
                "test", "qa", "quality", "testing", "test case", "test plan",
                "verification", "validate", "test coverage"
            ],
            "leader": [
                "metrics", "insights", "analytics", "report", "progress",
                "blocked", "blocker", "performance", "team", "status",
                "overview", "dashboard", "cycle time", "lead time"
            ],
        }

    async def start(self):
        """Start the router agent consumer"""
        try:
            logger.info("Starting Router Agent...")

            # Get Kafka producer
            self.producer = await get_kafka_producer()

            # Create consumer for user messages
            self.consumer = await create_consumer(
                consumer_id="router_agent",
                topics=[KafkaTopics.USER_MESSAGES],
                group_id="router_agent_group",
                auto_offset_reset="latest"
            )

            # Register message handler
            self.consumer.register_handler("user.message", self.handle_user_message)

            self.running = True
            logger.info("Router Agent started successfully")

            # Start consuming
            await self.consumer.consume()

        except Exception as e:
            logger.error(f"Error starting Router Agent: {e}")
            raise

    async def stop(self):
        """Stop the router agent"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("Router Agent stopped")

    async def handle_user_message(self, event_data: Dict[str, Any]):
        """
        Handle incoming user messages and route to appropriate agent

        Event structure:
        {
            "message_id": UUID,
            "project_id": UUID,
            "user_id": UUID,
            "content": str,
            "metadata": dict (optional)
        }
        """
        try:
            message_id = UUID(event_data["message_id"])
            project_id = UUID(event_data["project_id"])
            user_id = UUID(event_data["user_id"])
            content = event_data["content"]

            logger.info(f"Routing message {message_id} from user {user_id}")

            # Determine target agent
            agent_type, routing_reason, confidence = self.route_message(content)

            # Publish routing event
            routing_event = AgentRoutingEvent(
                message_id=message_id,
                project_id=project_id,
                routed_to=agent_type,
                routing_reason=routing_reason,
                confidence=confidence,
                timestamp=datetime.utcnow()
            )

            await self.producer.publish_event(
                topic=KafkaTopics.AGENT_ROUTING,
                event=routing_event.model_dump(),
                key=str(project_id)
            )

            # Create task for the target agent
            task_id = uuid.uuid4()
            agent_task = AgentTaskEvent(
                task_id=task_id,
                agent_type=agent_type,
                project_id=project_id,
                user_message_id=message_id,
                task_description=content,
                context={
                    "user_id": str(user_id),
                    "routing_reason": routing_reason,
                    "confidence": confidence,
                },
                timestamp=datetime.utcnow()
            )

            # Route to appropriate topic
            target_topic = self.get_agent_topic(agent_type)

            await self.producer.publish_event(
                topic=target_topic,
                event=agent_task.model_dump(),
                key=str(project_id)
            )

            logger.info(
                f"Routed message {message_id} to {agent_type} "
                f"(reason: {routing_reason}, confidence: {confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Error handling user message: {e}")

    def route_message(self, content: str) -> tuple[str, str, float]:
        """
        Determine which agent should handle the message

        Returns: (agent_type, routing_reason, confidence)
        """
        content_lower = content.lower()

        # 1. Check for explicit @mentions
        mentions = self.mention_pattern.findall(content_lower)
        if mentions:
            mention = mentions[0]
            # Normalize mention
            agent_map = {
                "ba": "ba",
                "dev": "dev",
                "developer": "dev",
                "tester": "tester",
                "test": "tester",
                "leader": "leader",
                "pm": "leader",
            }
            agent_type = agent_map.get(mention, "ba")
            return agent_type, f"Explicit mention: @{mention}", 1.0

        # 2. Keyword-based routing
        scores = {agent: 0 for agent in self.keywords.keys()}

        for agent, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    scores[agent] += 1

        # Find agent with highest score
        max_score = max(scores.values())

        if max_score > 0:
            # Get agent with highest score
            best_agent = max(scores.items(), key=lambda x: x[1])[0]
            confidence = min(max_score / 3.0, 1.0)  # Normalize confidence
            matched_keywords = [
                kw for kw in self.keywords[best_agent]
                if kw in content_lower
            ]
            return (
                best_agent,
                f"Keyword match: {', '.join(matched_keywords[:3])}",
                confidence
            )

        # 3. Default to BA agent (for general questions)
        return "ba", "Default routing (no specific keywords)", 0.5

    def get_agent_topic(self, agent_type: str) -> str:
        """Get Kafka topic for agent type"""
        topic_map = {
            "ba": KafkaTopics.AGENT_TASKS_BA,
            "dev": KafkaTopics.AGENT_TASKS_DEV,
            "tester": KafkaTopics.AGENT_TASKS_TESTER,
            "leader": KafkaTopics.AGENT_TASKS_LEADER,
        }
        return topic_map.get(agent_type, KafkaTopics.AGENT_TASKS_BA)


# Global router agent instance
router_agent = RouterAgent()
