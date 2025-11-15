"""Response Logger - Logs agent responses from Kafka to console"""

import logging
import asyncio
import json
from datetime import datetime
from app.kafka.schemas import AgentResponse
from app.kafka.consumer import KafkaConsumerService
from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class ResponseLogger:
    """Logs agent responses from Kafka - does not save to database"""

    def __init__(self):
        self.consumer = KafkaConsumerService(group_id="response-logger-consumer-group")
        logger.info("Response Logger initialized")

    async def handle_agent_response(self, response_data: dict):
        """Handle incoming agent response from Kafka"""
        try:
            # Parse agent response
            response = AgentResponse(**response_data)

            # Log the response with nice formatting
            logger.info("=" * 80)
            logger.info(f"📬 AGENT RESPONSE RECEIVED")
            logger.info(f"   Task ID: {response.task_id}")
            logger.info(f"   Agent: {response.agent_type} ({response.agent_id})")
            logger.info(f"   Status: {response.status}")

            if response.execution_time_ms:
                logger.info(f"   Execution Time: {response.execution_time_ms}ms")

            if response.result:
                logger.info(f"   Result:")
                # Pretty print the result
                result_str = json.dumps(response.result, indent=4, ensure_ascii=False)
                for line in result_str.split('\n'):
                    logger.info(f"     {line}")

            if response.error:
                logger.error(f"   ❌ Error: {response.error}")

            logger.info(f"   Completed At: {response.completed_at}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error handling agent response: {e}")

    async def start(self):
        """Start the response logger and begin consuming agent responses"""
        logger.info("🚀 Starting Response Logger")

        # Register response handler
        self.consumer.register_handler(
            KafkaTopics.AGENT_RESPONSES,
            self.handle_agent_response
        )

        # Initialize consumer
        self.consumer.initialize([KafkaTopics.AGENT_RESPONSES])

        # Start consuming
        await self.consumer.start_consuming()


# Global response logger instance
response_logger = ResponseLogger()
