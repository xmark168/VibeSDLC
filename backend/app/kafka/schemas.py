"""Kafka message schemas for VibeSDLC"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgentTaskType(str, Enum):
    """Types of tasks that can be sent to agents"""
    HELLO = "hello"
    ANALYZE_STORY = "analyze_story"
    GENERATE_CODE = "generate_code"
    RUN_TESTS = "run_tests"
    REVIEW_CODE = "review_code"


class AgentTaskStatus(str, Enum):
    """Status of agent tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTask(BaseModel):
    """Message schema for tasks sent to agents"""
    task_id: str = Field(..., description="Unique task identifier")
    task_type: AgentTaskType = Field(..., description="Type of task")
    agent_type: str = Field(..., description="Target agent type (developer, tester, etc.)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task-specific data")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=lowest, 10=highest)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    story_id: Optional[int] = Field(None, description="Related story ID if applicable")
    project_id: Optional[int] = Field(None, description="Related project ID if applicable")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123",
                "task_type": "hello",
                "agent_type": "developer",
                "payload": {"message": "Hello from backend!"},
                "priority": 5,
                "story_id": 1,
                "project_id": 1
            }
        }


class AgentResponse(BaseModel):
    """Message schema for agent responses"""
    task_id: str = Field(..., description="Original task identifier")
    agent_id: str = Field(..., description="Agent identifier")
    agent_type: str = Field(..., description="Agent type")
    status: AgentTaskStatus = Field(..., description="Task completion status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123",
                "agent_id": "developer_001",
                "agent_type": "developer",
                "status": "completed",
                "result": {"message": "Hello! I'm a developer agent."},
                "execution_time_ms": 150
            }
        }


class StoryEvent(BaseModel):
    """Message schema for story events"""
    event_type: str = Field(..., description="Type of event (created, updated, status_changed, assigned)")
    story_id: int = Field(..., description="Story ID")
    project_id: int = Field(..., description="Project ID")
    epic_id: Optional[int] = Field(None, description="Epic ID if applicable")
    changes: Dict[str, Any] = Field(default_factory=dict, description="What changed")
    triggered_by: int = Field(..., description="User ID who triggered the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "status_changed",
                "story_id": 42,
                "project_id": 1,
                "changes": {"status": {"from": "TODO", "to": "IN_PROGRESS"}},
                "triggered_by": 1
            }
        }


class AgentStatusMessage(BaseModel):
    """Message schema for agent status updates"""
    agent_id: str = Field(..., description="Agent identifier")
    agent_type: str = Field(..., description="Agent type")
    status: str = Field(..., description="Agent status (online, offline, busy, idle)")
    current_task_id: Optional[str] = Field(None, description="Current task ID if busy")
    workload: int = Field(default=0, description="Current workload count")
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "developer_001",
                "agent_type": "developer",
                "status": "idle",
                "workload": 0
            }
        }
