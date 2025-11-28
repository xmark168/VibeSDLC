"""Agent execution, metrics, and question models."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import JSON, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Column

from app.models.base import (
    BaseModel, AgentExecutionStatus, QuestionType, QuestionStatus
)


class AgentExecution(BaseModel, table=True):
    __tablename__ = "agent_executions"

    project_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE", use_alter=True, name="fk_agent_executions_project_id"),
            index=True,
            nullable=False
        )
    )

    agent_name: str = Field(nullable=False)
    agent_type: str = Field(nullable=False)

    status: AgentExecutionStatus = Field(default=AgentExecutionStatus.PENDING)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None)

    trigger_message_id: UUID | None = Field(default=None, foreign_key="messages.id", ondelete="SET NULL")
    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")

    token_used: int = Field(default=0)
    llm_calls: int = Field(default=0)

    error_message: str | None = Field(default=None, sa_column=Column(Text))
    error_traceback: str | None = Field(default=None, sa_column=Column(Text))

    result: dict | None = Field(default=None, sa_column=Column(JSON))
    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))


class AgentMetricsSnapshot(BaseModel, table=True):
    __tablename__ = "agent_metrics_snapshots"

    snapshot_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    pool_name: str = Field(nullable=False, index=True)

    total_agents: int = Field(default=0)
    idle_agents: int = Field(default=0)
    busy_agents: int = Field(default=0)
    error_agents: int = Field(default=0)

    total_executions: int = Field(default=0)
    successful_executions: int = Field(default=0)
    failed_executions: int = Field(default=0)

    total_tokens: int = Field(default=0)
    total_llm_calls: int = Field(default=0)

    avg_execution_duration_ms: float | None = Field(default=None)

    process_count: int = Field(default=0)
    total_capacity: int = Field(default=0)
    used_capacity: int = Field(default=0)
    utilization_percentage: float | None = Field(default=None)

    snapshot_metadata: dict | None = Field(default=None, sa_column=Column(JSON))


class AgentQuestion(BaseModel, table=True):
    __tablename__ = "agent_questions"
    
    project_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE", use_alter=True, name="fk_agent_questions_project_id"),
            nullable=False
        )
    )
    agent_id: UUID = Field(foreign_key="agents.id", ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="users.id")
    
    question_type: QuestionType = Field(sa_column=Column(SQLEnum(QuestionType)))
    question_text: str = Field(sa_column=Column(Text))
    
    options: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allow_multiple: bool = Field(default=False)
    
    proposed_data: dict | None = Field(default=None, sa_column=Column(JSON))
    explanation: str | None = Field(default=None, sa_column=Column(Text))
    
    answer: str | None = Field(default=None, sa_column=Column(Text))
    selected_options: list[str] | None = Field(default=None, sa_column=Column(JSON))
    approved: bool | None = Field(default=None)
    modified_data: dict | None = Field(default=None, sa_column=Column(JSON))
    
    status: QuestionStatus = Field(
        default=QuestionStatus.WAITING_ANSWER,
        sa_column=Column(SQLEnum(QuestionStatus))
    )
    
    task_id: UUID
    execution_id: UUID | None = None
    task_context: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    expires_at: datetime
    answered_at: datetime | None = None
    
    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
