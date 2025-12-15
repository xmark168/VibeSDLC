"""Base model and common enums for all models."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


# ==================== ENUMS ====================

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class LimitType(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class StoryStatus(str, Enum):
    TODO = "Todo"
    IN_PROGRESS = "InProgress"
    REVIEW = "Review"
    DONE = "Done"
    ARCHIVED = "Archived"


class StoryAgentState(str, Enum):
    """Agent execution state on a story. Resets when story changes column."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAUSED = "PAUSED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"  # User requested cancel, waiting for agent to acknowledge
    CANCELED = "CANCELED"  # Agent acknowledged and stopped
    FINISHED = "FINISHED"


class StoryType(str, Enum):
    USER_STORY = "UserStory"


class AuthorType(str, Enum):
    USER = "user"
    AGENT = "agent"


class MessageVisibility(str, Enum):
    USER_MESSAGE = "user_message"
    SYSTEM_LOG = "system_log"


class AgentStatus(str, Enum):
    created = "created"
    starting = "starting"
    running = "running"
    idle = "idle"
    busy = "busy"
    stopping = "stopping"
    stopped = "stopped"
    error = "error"
    terminated = "terminated"


class PoolType(str, Enum):
    FREE = "free"
    PAID = "paid"


class EpicStatus(str, Enum):
    PLANNED = "Planned"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class AgentExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QuestionType(str, Enum):
    OPEN = "open"
    MULTICHOICE = "multichoice"
    APPROVAL = "approval"


class QuestionStatus(str, Enum):
    WAITING_ANSWER = "waiting_answer"
    ANSWERED = "answered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ArtifactType(str, Enum):
    PRD = "prd"
    ARCHITECTURE = "architecture"
    API_SPEC = "api_spec"
    DATABASE_SCHEMA = "database_schema"
    USER_STORIES = "user_stories"
    CODE = "code"
    TEST_PLAN = "test_plan"
    REVIEW = "review"
    ANALYSIS = "analysis"


class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class OrderType(str, Enum):
    SUBSCRIPTION = "subscription"
    CREDIT = "credit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"
    EXPIRED = "expired"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


# ==================== BASE MODEL ====================

class BaseModel(SQLModel):
    """Base model with common fields."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False,
    )
