"""
CrewAI Events Module

Exports event system components for Kafka integration
"""

from app.crews.events import event_schemas, kafka_producer, kafka_consumer

__all__ = [
    "event_schemas",
    "kafka_producer",
    "kafka_consumer",
]
