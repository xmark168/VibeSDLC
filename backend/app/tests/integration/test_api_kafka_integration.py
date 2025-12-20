"""
Integration test example: API ↔ Kafka Integration
Using the testing plan from TESTING_PLAN.md
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.main import app
from app.kafka.producer import get_kafka_producer
from app.kafka.event_schemas import UserMessageEvent, KafkaTopics
from app.models import Project


@pytest.fixture
def test_client():
    """Create test client for API testing."""
    with TestClient(app) as client:
        yield client


def test_send_message_api_kafka_integration(test_client: TestClient):
    """
    Integration test example: API → Kafka Messaging
    Following the test case described in TESTING_PLAN.md section 7.2
    """
    # Given: Valid test data
    project_id = str(uuid4())
    user_id = str(uuid4())
    message_content = "Test message for Kafka integration"
    
    message_data = {
        "project_id": project_id,
        "user_id": user_id,
        "content": message_content,
        "message_type": "user_message"
    }
    
    # Mock Kafka producer to capture published events
    with patch('app.kafka.producer.get_kafka_producer') as mock_get_producer:
        mock_producer = MagicMock()
        mock_get_producer.return_value = mock_producer
        
        # When: Send message via API
        response = test_client.post("/messages/", json=message_data)
        
        # Then: Verify API response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}, response: {response.text}"
        
        # Then: Verify Kafka producer was called correctly
        assert mock_producer.publish.called, "Kafka producer was not called"
        
        # Capture the actual call to verify the parameters
        call_args = mock_producer.publish.call_args
        assert call_args is not None, "Kafka producer publish was not called with correct parameters"
        
        # Verify topic and event type
        call_kwargs = call_args.kwargs
        assert call_kwargs['topic'] in [topic.value for topic in KafkaTopics], f"Invalid topic: {call_kwargs.get('topic')}"
        
        # Verify the event schema
        event = call_kwargs.get('event')
        assert event is not None, "No event was published to Kafka"
        assert hasattr(event, 'content'), "Event should have content attribute"
        assert event.content == message_content, f"Expected content '{message_content}', got '{event.content}'"
        
        print(f"✓ API ↔ Kafka integration test passed: Message '{message_content}' published to {call_kwargs['topic']}")


def test_create_story_kafka_integration(test_client: TestClient):
    """
    Integration test: Story creation API → Kafka event publishing
    """
    # Given: Valid test data
    project_id = str(uuid4())
    story_data = {
        "title": "Kafka Integration Story",
        "description": "Testing Kafka message after API call",
        "project_id": project_id,
        "status": "todo"
    }
    
    # Mock Kafka producer
    with patch('app.kafka.producer.get_kafka_producer') as mock_get_producer:
        mock_producer = MagicMock()
        mock_get_producer.return_value = mock_producer
        
        # When: Create story via API
        response = test_client.post("/stories/", json=story_data)
        
        # Then: Verify API response
        assert response.status_code == 200
        response_data = response.json()
        
        # Then: Verify Kafka producer was called for story creation event
        # Check if any Kafka publish calls were made
        assert mock_producer.publish.called, "Kafka producer should be called when creating story"
        
        # Print details about the calls made
        print(f"✓ Kafka publish called {mock_producer.publish.call_count} times during story creation")
        for i, call in enumerate(mock_producer.publish.call_args_list):
            topic = call.kwargs.get('topic')
            event = call.kwargs.get('event')
            print(f"  Call {i+1}: Topic={topic}, Event type={type(event).__name__}")
            
        print(f"✓ Story creation → Kafka integration test passed")


def test_webhook_message_to_kafka_integration(test_client: TestClient):
    """
    Integration test: Webhook API → Kafka routing
    """
    # Given: Test message data that would come from frontend
    project_id = str(uuid4())
    user_message = {
        "project_id": project_id,
        "user_id": str(uuid4()),
        "content": "User message from frontend via WebSocket",
        "message_type": "user_message",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    # Mock the Kafka producer
    with patch('app.kafka.producer.get_kafka_producer') as mock_get_producer:
        mock_producer = MagicMock()
        mock_get_producer.return_value = mock_producer
        
        # When: Send message to webhook endpoint (simulating frontend message)
        response = test_client.post("/messages/webhook", json=user_message)
        
        # Then: Verify API response (could be 200 or 201 depending on implementation)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        
        # Then: Verify message was sent to Kafka
        assert mock_producer.publish.called, "Message should be published to Kafka"
        
        # Verify the message was sent to the correct topic
        call_args = mock_producer.publish.call_args
        if call_args:
            topic = call_args.kwargs.get('topic')
            event = call_args.kwargs.get('event')
            
            # Should be sent to user message topic
            assert topic is not None, "Topic should be specified"
            print(f"✓ Webhook message sent to Kafka topic: {topic}")
        
        print(f"✓ Webhook → Kafka integration test passed")


if __name__ == "__main__":
    # Run the tests directly if needed
    pytest.main([__file__, "-v"])