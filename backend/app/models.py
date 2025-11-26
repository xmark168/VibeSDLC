from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import JSON, Text, Enum as SQLEnum, UniqueConstraint
from typing import Optional

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


class Agent(BaseModel, table=True):
    __tablename__ = "agents"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    persona_template_id: UUID | None = Field(
        default=None,
        foreign_key="agent_persona_templates.id",
        ondelete="RESTRICT"
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
