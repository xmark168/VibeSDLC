from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlalchemy import JSON, BigInteger, Text, Enum as SQLEnum, UniqueConstraint
from sqlmodel import Field, SQLModel, Relationship, Column

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


class StoryType(str, Enum):
    USER_STORY = "UserStory"
    ENABLER_STORY = "EnablerStory"


class StoryPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class BaseModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False,
    )


class AgentPersonaTemplate(BaseModel, table=True):
    __tablename__ = "agent_persona_templates"
    
    name: str = Field(nullable=False, index=True)
    role_type: str = Field(nullable=False, index=True)
    
    personality_traits: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    communication_style: str = Field(nullable=False)
    
    persona_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0)
    
    agents: list["Agent"] = Relationship(back_populates="persona_template")
    
    __table_args__ = (
        UniqueConstraint('name', 'role_type', name='uq_persona_name_role'),
    )


class User(BaseModel, table=True):
    __tablename__ = "users"

    username : str | None = Field(default=None, max_length=50, nullable=True)
    full_name: str | None = Field(default=None, max_length=50, nullable=True)
    hashed_password: str = Field(nullable=True, sa_column_kwargs={"name": "password_hash"})
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    
    address: str | None = Field(default=None, nullable=True)
    balance: float = Field(default=0.0, nullable=True)
    is_active: bool = Field(default=True, nullable=True)
    failed_login_attempts: int = Field(default=0, nullable=False)
    locked_until: datetime | None = Field(default=None)
    two_factor_enabled: bool = Field(default=False, nullable=True)
    
    role: Role = Field(default=Role.USER, nullable=False)
    is_locked: bool = Field(default=False, nullable=False)
    login_provider: bool = Field(default=False, nullable=False)

    owned_projects: list["Project"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    comments: list["Comment"] = Relationship(
        back_populates="commenter",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    user_subscriptions: list["Subscription"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class EpicStatus(str, Enum):
    PLANNED = "Planned"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class Epic(BaseModel, table=True):
    __tablename__ = "epics"

    title: str
    description: str | None = Field(default=None, sa_column=Column(Text))
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE")

    domain: str | None = Field(default=None)
    epic_status: EpicStatus = Field(default=EpicStatus.PLANNED)

    project: "Project" = Relationship(back_populates="epics")
    stories: list["Story"] = Relationship(back_populates="epic")


class Project(BaseModel, table=True):
    __tablename__ = "projects"

    code: str
    name: str
    owner_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    is_init: bool = Field(default=False)

    is_private: bool = Field(default=True)
    tech_stack: str = Field(default="nodejs-react")
    wip_data: dict | None = Field(default=None, sa_column=Column(JSON))

    project_path: str | None = Field(default=None, max_length=500)
    
    active_agent_id: UUID | None = Field(
        default=None,
        foreign_key="agents.id",
        ondelete="SET NULL"
    )
    active_agent_updated_at: datetime | None = Field(default=None)
    
    websocket_connected: bool = Field(default=False)
    websocket_last_seen: datetime | None = Field(default=None)
    
    # Token budget fields for cost control
    token_budget_daily: int = Field(default=100000)  # 100K tokens/day
    token_budget_monthly: int = Field(default=2000000)  # 2M tokens/month
    tokens_used_today: int = Field(default=0)
    tokens_used_this_month: int = Field(default=0)
    budget_last_reset_daily: datetime | None = Field(default=None)
    budget_last_reset_monthly: datetime | None = Field(default=None)
    
    owner: User = Relationship(back_populates="owned_projects")
    stories: list["Story"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    epics: list["Epic"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    agents: list["Agent"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "foreign_keys": "[Agent.project_id]"
        },
    )

    rules: Optional["ProjectRules"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )


class WorkflowPolicy(BaseModel, table=True):
    __tablename__ = "workflow_policies"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)
    from_status: str = Field(max_length=50, nullable=False)
    to_status: str = Field(max_length=50, nullable=False)
    criteria: dict | None = Field(default=None, sa_column=Column(JSON))
    required_role: str | None = Field(default=None, max_length=50)
    is_active: bool = Field(default=True, nullable=False)

    project: "Project" = Relationship()


class Story(BaseModel, table=True):
    __tablename__ = "stories"

    project_id: UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True
    )
    parent_id: UUID | None = Field(
        default=None, foreign_key="stories.id", ondelete="SET NULL"
    )

    type: StoryType = Field(default=StoryType.USER_STORY)
    title: str
    description: str | None = Field(default=None, sa_column=Column(Text))
    status: StoryStatus = Field(default=StoryStatus.TODO)

    epic_id: UUID | None = Field(default=None, foreign_key="epics.id", ondelete="SET NULL")

    acceptance_criteria: str | None = Field(default=None, sa_column=Column(Text))

    assignee_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    reviewer_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )

    rank: int | None = Field(default=None)
    estimate_value: int | None = Field(default=None)
    story_point: int | None = Field(default=None)
    priority: int | None = Field(default=None)

    story_priority: StoryPriority | None = Field(default=None)
    dependencies: list = Field(default_factory=list, sa_column=Column(JSON))

    pause: bool = Field(default=False)
    deadline: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    started_at: datetime | None = Field(default=None)
    review_started_at: datetime | None = Field(default=None)

    token_used: int | None = Field(default=None)

    project: Project = Relationship(back_populates="stories")
    epic: Optional["Epic"] = Relationship(back_populates="stories")
    parent: Optional["Story"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Story.id"},
    )
    children: list["Story"] = Relationship(back_populates="parent")
    comments: list["Comment"] = Relationship(
        back_populates="story",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    activities: list["IssueActivity"] = Relationship(
        back_populates="story", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @property
    def cycle_time_hours(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 3600
        return None

    @property
    def lead_time_hours(self) -> float | None:
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds() / 3600
        return None

    @property
    def age_in_current_status_hours(self) -> float:
        status_start_time = self.created_at

        if self.status == StoryStatus.IN_PROGRESS and self.started_at:
            status_start_time = self.started_at
        elif self.status == StoryStatus.REVIEW and self.review_started_at:
            status_start_time = self.review_started_at
        elif self.status == StoryStatus.DONE and self.completed_at:
            status_start_time = self.completed_at

        current_time = datetime.now(timezone.utc)
        return (current_time - status_start_time).total_seconds() / 3600


class Comment(BaseModel, table=True):
    __tablename__ = "comments"

    backlog_item_id: UUID = Field(
        foreign_key="stories.id", nullable=False, ondelete="CASCADE"
    )
    commenter_id: UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    content: str

    story: Story = Relationship(back_populates="comments")
    commenter: User = Relationship(back_populates="comments")


class IssueActivity(BaseModel, table=True):
    __tablename__ = "issue_activities"

    issue_id: UUID = Field(
        foreign_key="stories.id", nullable=False, ondelete="CASCADE"
    )
    actor_id: str | None = Field(default=None)
    actor_name: str | None = Field(default=None)

    title_from: str | None = Field(default=None)
    title_to: str | None = Field(default=None)
    status_from: str | None = Field(default=None)
    status_to: str | None = Field(default=None)
    assignee_from: str | None = Field(default=None)
    assignee_to: str | None = Field(default=None)
    reviewer_from: str | None = Field(default=None)
    reviewer_to: str | None = Field(default=None)
    rank_from: int | None = Field(default=None)
    rank_to: int | None = Field(default=None)
    estimate_from: int | None = Field(default=None)
    estimate_to: int | None = Field(default=None)
    deadline_from: datetime | None = Field(default=None)
    deadline_to: datetime | None = Field(default=None)
    type_from: str | None = Field(default=None)
    type_to: str | None = Field(default=None)
    note: str | None = Field(default=None)

    story: Story = Relationship(back_populates="activities") 

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


class AgentPool(BaseModel, table=True):
    __tablename__ = "agent_pools"
    
    pool_name: str = Field(unique=True, nullable=False)
    role_type: str | None = Field(default=None, index=True)
    
    pool_type: PoolType = Field(default=PoolType.FREE, index=True)
    
    max_agents: int = Field(default=100)
    health_check_interval: int = Field(default=60)
    
    llm_model_config: dict | None = Field(default=None, sa_column=Column(JSON))
    allowed_template_ids: list[str] | None = Field(default=None, sa_column=Column(JSON))
    
    is_active: bool = Field(default=True, index=True)
    last_started_at: datetime | None = Field(default=None)
    last_stopped_at: datetime | None = Field(default=None)
    
    total_spawned: int = Field(default=0)
    total_terminated: int = Field(default=0)
    current_agent_count: int = Field(default=0)
    
    created_by: UUID | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL"
    )
    updated_by: UUID | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL"
    )
    auto_created: bool = Field(default=False)
    
    agents: list["Agent"] = Relationship(back_populates="pool")
    metrics: list["AgentPoolMetrics"] = Relationship(
        back_populates="pool",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class AgentPoolMetrics(BaseModel, table=True):
    __tablename__ = "agent_pool_metrics"
    
    pool_id: UUID = Field(
        foreign_key="agent_pools.id",
        nullable=False,
        ondelete="CASCADE",
        index=True
    )
    
    period_start: datetime = Field(nullable=False, index=True)
    period_end: datetime = Field(nullable=False)
    
    total_tokens_used: int = Field(default=0)
    tokens_per_model: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    total_requests: int = Field(default=0)
    requests_per_model: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    peak_agent_count: int = Field(default=0)
    avg_agent_count: float = Field(default=0.0)
    
    total_executions: int = Field(default=0)
    successful_executions: int = Field(default=0)
    failed_executions: int = Field(default=0)
    
    avg_execution_duration_ms: float | None = Field(default=None)
    
    snapshot_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    
    pool: "AgentPool" = Relationship(back_populates="metrics")


class Agent(BaseModel, table=True):
    __tablename__ = "agents"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    persona_template_id: UUID | None = Field(
        default=None,
        foreign_key="agent_persona_templates.id",
        ondelete="RESTRICT"
    )
    
    pool_id: UUID | None = Field(
        default=None,
        foreign_key="agent_pools.id",
        ondelete="SET NULL",
        index=True
    )

    name: str
    human_name: str = Field(nullable=False)
    role_type: str = Field(nullable=False)
    agent_type: str | None = Field(default=None)

    personality_traits: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    communication_style: str | None = Field(default=None)
    persona_metadata: dict | None = Field(default=None, sa_column=Column(JSON))

    status: AgentStatus = Field(default=AgentStatus.idle)

    persona_template: Optional["AgentPersonaTemplate"] = Relationship(back_populates="agents")
    pool: Optional["AgentPool"] = Relationship(back_populates="agents")
    project: "Project" = Relationship(
        back_populates="agents",
        sa_relationship_kwargs={
            "foreign_keys": "[Agent.project_id]"
        }
    )
    messages: list["Message"] = Relationship(back_populates="agent")


class Message(BaseModel, table=True):
    __tablename__ = "messages"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    author_type: AuthorType = Field(default=AuthorType.USER, nullable=False)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="SET NULL")

    content: str

    visibility: MessageVisibility = Field(
        default=MessageVisibility.USER_MESSAGE,
        sa_column=Column(
            SQLEnum(MessageVisibility, name='messagevisibility', native_enum=True, values_callable=lambda x: [e.value for e in x]),
            nullable=False
        )
    )

    message_type: str = Field(default="text", nullable=True)
    structured_data: dict | None = Field(default=None, sa_column=Column(JSON))
    message_metadata: dict | None = Field(default=None, sa_column=Column(JSON))

    agent: Agent | None = Relationship(back_populates="messages")


class RefreshToken(BaseModel, table=True):
    __tablename__ = "refresh_tokens"

    token: str = Field(unique=True, index=True, max_length=255)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    expires_at: datetime = Field(nullable=False)
    is_revoked: bool = Field(default=False, nullable=False)

    family_id: UUID = Field(nullable=False, index=True)
    parent_token_id: UUID | None = Field(default=None, foreign_key="refresh_tokens.id", ondelete="SET NULL")

    user: User = Relationship()
    parent: Optional["RefreshToken"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "RefreshToken.id"},
    )
    children: list["RefreshToken"] = Relationship(back_populates="parent")


class ProjectRules(BaseModel, table=True):
    __tablename__ = "projectrules"

    project_id: UUID = Field(foreign_key="projects.id", unique=True, nullable=False, ondelete="CASCADE")

    po_prompt: str | None = Field(default=None, sa_column=Column(Text))
    dev_prompt: str | None = Field(default=None, sa_column=Column(Text))
    tester_prompt: str | None = Field(default=None, sa_column=Column(Text))

    project: Project = Relationship(back_populates="rules")


class AgentExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecution(BaseModel, table=True):
    __tablename__ = "agent_executions"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

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


class AgentConversation(BaseModel, table=True):
    __tablename__ = "agent_conversations"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)
    execution_id: UUID | None = Field(default=None, foreign_key="agent_executions.id", ondelete="CASCADE")

    sender_type: str = Field(nullable=False)
    sender_name: str = Field(nullable=False)
    recipient_type: str | None = Field(default=None)
    recipient_name: str | None = Field(default=None)

    message_type: str = Field(nullable=False)
    content: str = Field(sa_column=Column(Text))
    structured_data: dict | None = Field(default=None, sa_column=Column(JSON))

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


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel, table=True):
    __tablename__ = "approval_requests"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)
    execution_id: UUID | None = Field(default=None, foreign_key="agent_executions.id", ondelete="CASCADE")

    request_type: str = Field(nullable=False)
    agent_name: str = Field(nullable=False)

    proposed_data: dict = Field(sa_column=Column(JSON))
    explanation: str | None = Field(default=None, sa_column=Column(Text))

    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    approved_by_user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    approved_at: datetime | None = Field(default=None)

    user_feedback: str | None = Field(default=None, sa_column=Column(Text))
    modified_data: dict | None = Field(default=None, sa_column=Column(JSON))

    applied: bool = Field(default=False)
    applied_at: datetime | None = Field(default=None)
    created_entity_id: UUID | None = Field(default=None)


class QuestionType(str, Enum):
    OPEN = "open"
    MULTICHOICE = "multichoice"


class QuestionStatus(str, Enum):
    WAITING_ANSWER = "waiting_answer"
    ANSWERED = "answered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AgentQuestion(BaseModel, table=True):
    __tablename__ = "agent_questions"
    
    project_id: UUID = Field(foreign_key="projects.id", ondelete="CASCADE")
    agent_id: UUID = Field(foreign_key="agents.id", ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="users.id")
    
    question_type: QuestionType = Field(sa_column=Column(SQLEnum(QuestionType)))
    question_text: str = Field(sa_column=Column(Text))
    
    options: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allow_multiple: bool = Field(default=False)
    
    answer: str | None = Field(default=None, sa_column=Column(Text))
    selected_options: list[str] | None = Field(default=None, sa_column=Column(JSON))
    
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


class Artifact(BaseModel, table=True):
    __tablename__ = "artifacts"
    
    project_id: UUID = Field(foreign_key="projects.id", ondelete="CASCADE", index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="SET NULL")
    agent_name: str = Field(nullable=False)
    
    artifact_type: ArtifactType = Field(sa_column=Column(SQLEnum(ArtifactType)))
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text))
    
    content: dict = Field(sa_column=Column(JSON))
    file_path: str | None = Field(default=None)
    
    version: int = Field(default=1)
    parent_artifact_id: UUID | None = Field(default=None, foreign_key="artifacts.id", ondelete="SET NULL")
    
    status: ArtifactStatus = Field(default=ArtifactStatus.DRAFT, sa_column=Column(SQLEnum(ArtifactStatus)))
    
    reviewed_by_user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    reviewed_at: datetime | None = Field(default=None)
    review_feedback: str | None = Field(default=None, sa_column=Column(Text))
    
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    
    project: "Project" = Relationship()
    agent: Optional["Agent"] = Relationship()
    reviewed_by: Optional["User"] = Relationship()
    parent: Optional["Artifact"] = Relationship(
        sa_relationship_kwargs={
            "remote_side": "[Artifact.id]",
            "foreign_keys": "[Artifact.parent_artifact_id]"
        }
    )


# ==================== BILLING & PAYMENT MODELS ====================

class OrderType(str, Enum):
    """Type of order"""
    SUBSCRIPTION = "subscription"
    ADDON = "addon"


class OrderStatus(str, Enum):
    """Status of an order"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"


class InvoiceStatus(str, Enum):
    """Status of an invoice"""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


# ==================== Plans ====================
class Plan(BaseModel, table=True):
    __tablename__ = "plans"

    code: str | None = Field(default=None, sa_column=Column(Text)) # 'FREE', 'PLUS', 'PRO'
    name: str | None = Field(default=None, sa_column=Column(Text))
    description: str | None = Field(default=None, sa_column=Column(Text))

    monthly_price: int | None = Field(default=None)
    yearly_discount_percentage: float | None = Field(default=None)  # Discount % for yearly billing (0-100)
    currency: str | None = Field(default=None, sa_column=Column(Text)) # VND
    monthly_credits: int | None = Field(default=None)
    additional_credit_price: int | None = Field(default=None)  # Price to buy 100 additional credits
    available_project: int | None = Field(default=None)
    is_active: bool = Field(default=True, nullable=True)

    tier: str | None = Field(
        default="pay",
        sa_column=Column(Text)
    )
    # 'free' | 'pay'

    sort_index: int | None = Field(default=0)
    # số thứ tự để sắp xếp trên UI

    is_featured: bool = Field(default=False)  # gói nổi bật (đặt ở giữa + badge "Popular")

    is_custom_price: bool = Field(default=False)  # true -> hiển thị "Custom" / "Liên hệ"

    features_text: str | None = Field(default=None, sa_column=Column(Text))

    plan_subscriptions: list["Subscription"] = Relationship(
        back_populates="plan", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @property
    def yearly_price(self) -> int | None:
        """Calculate yearly price from monthly price and discount percentage"""
        if self.monthly_price is not None and self.yearly_discount_percentage is not None:
            annual_monthly_cost = self.monthly_price * 12
            yearly_price = annual_monthly_cost * (1 - self.yearly_discount_percentage / 100)
            return round(yearly_price)
        return None

class Subscription(BaseModel, table=True):
    __tablename__ = "subscriptions"

    user_id: UUID  | None = Field(foreign_key="users.id", nullable=True, ondelete="CASCADE")
    plan_id: UUID = Field(foreign_key="plans.id", nullable=True, ondelete="CASCADE")

    status: str | None = Field(default=None, sa_column=Column(Text)) # 'pending', 'active', 'expired', 'canceled'
    start_at: datetime | None = Field(default=None)
    end_at: datetime | None = Field(default=None)
    auto_renew: bool = Field(default=True, nullable=True)

    user: User = Relationship(back_populates="user_subscriptions")
    plan: Plan = Relationship(back_populates="plan_subscriptions")

    subscription_wallets: list["CreditWallet"] = Relationship(
        back_populates="subscription", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class CreditWallet(BaseModel, table=True):
    __tablename__ = "credit_wallets"

    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    wallet_type: str | None = Field(default=None, sa_column=Column(Text)) # subscription, addon

    subscription_id: UUID | None = Field(default=None, foreign_key="subscriptions.id", ondelete="CASCADE")
    period_start: datetime | None = Field(default=None)
    period_end: datetime | None = Field(default=None)

    total_credits: int | None = Field(default=None)
    used_credits: int | None = Field(default=None)

    # Relationships
    user: User | None = Relationship()
    subscription: Optional["Subscription"] = Relationship(back_populates="subscription_wallets")
    credit_activities: list["CreditActivity"] = Relationship(
        back_populates="wallet", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class CreditActivity(BaseModel, table=True):
    __tablename__ = "credit_activities"

    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="CASCADE")
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="CASCADE")
    wallet_id: UUID | None = Field(default=None, foreign_key="credit_wallets.id", ondelete="CASCADE")

    amount: int | None = Field(default=None)
    reason: str | None = Field(default=None, sa_column=Column(Text))
    activity_type: str | None = Field(default=None, sa_column=Column(Text)) # cộng, trừ

    # Relationships
    user: User | None = Relationship()
    agent: Agent | None = Relationship()
    wallet: CreditWallet | None = Relationship(back_populates="credit_activities")


class Order(BaseModel, table=True):
    __tablename__ = "orders"

    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    order_type: OrderType = Field(nullable=False)  # subscription or addon
    subscription_id: UUID | None = Field(default=None, foreign_key="subscriptions.id", ondelete="SET NULL")

    amount: float = Field(nullable=False)
    status: OrderStatus = Field(default=OrderStatus.PENDING, nullable=False)
    paid_at: datetime | None = Field(default=None)
    is_active: bool = Field(default=True, nullable=False)

    # PayOS Integration fields
    payos_order_code: int | None = Field(default=None, sa_column=Column(BigInteger, unique=True, index=True))
    payos_transaction_id: str | None = Field(default=None, sa_column=Column(Text))
    payment_link_id: str | None = Field(default=None, sa_column=Column(Text))
    qr_code: str | None = Field(default=None, sa_column=Column(Text))  # Base64 QR code
    checkout_url: str | None = Field(default=None, sa_column=Column(Text))

    # Payment details
    billing_cycle: str | None = Field(default="monthly", sa_column=Column(Text))  # monthly, yearly
    plan_code: str | None = Field(default=None, sa_column=Column(Text))  # Store plan code for reference

    # Relationships
    user: User = Relationship()
    subscription: Optional["Subscription"] = Relationship()
    invoices: list["Invoice"] = Relationship(
        back_populates="order", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Invoice(BaseModel, table=True):
    __tablename__ = "invoices"

    order_id: UUID = Field(foreign_key="orders.id", nullable=False, ondelete="CASCADE")
    invoice_number: str = Field(unique=True, index=True, nullable=False)

    billing_name: str = Field(nullable=False)
    billing_address: str | None = Field(default=None, sa_column=Column(Text))

    amount: float = Field(nullable=False)
    currency: str = Field(default="VND", nullable=False)

    issue_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT, nullable=False)

    # Relationships
    order: Order = Relationship(back_populates="invoices")

