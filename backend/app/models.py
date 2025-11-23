from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import JSON, Text
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
    """Story priority for INVEST principle (Negotiable)"""
    HIGH = "High"  # Must have for MVP
    MEDIUM = "Medium"  # Should have
    LOW = "Low"  # Nice to have


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


# Shared properties
class User(BaseModel, table=True):
    __tablename__ = "users"

    username : str | None = Field(default=None, max_length=50, nullable=True)
    full_name: str | None = Field(default=None, max_length=50, nullable=True)
    hashed_password: str = Field(nullable=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    role: Role = Field(default=Role.USER, nullable=True)

    # Account status fields for security
    is_active: bool = Field(default=True, nullable=True)
    is_locked: bool = Field(default=False, nullable=False)
    locked_until: datetime | None = Field(default=None)
    failed_login_attempts: int = Field(default=0, nullable=False)

    login_provider: bool = Field(default=False, nullable=False)

    owned_projects: list["Project"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    comments: list["Comment"] = Relationship(
        back_populates="commenter",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class EpicStatus(str, Enum):
    """Status of an Epic"""
    PLANNED = "Planned"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class Epic(BaseModel, table=True):
    """Epic model for grouping stories"""
    __tablename__ = "epics"

    title: str
    description: str | None = Field(default=None, sa_column=Column(Text))
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE")

    # BA workflow fields
    domain: str | None = Field(default=None)  # Feature domain (e.g., Product, Cart, Order, Payment)
    epic_status: EpicStatus = Field(default=EpicStatus.PLANNED)

    # Relationships
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

    # File system path for project files (auto-generated: projects/{project_id})
    project_path: str | None = Field(default=None, max_length=500)
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
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    # TraDS ============= Project Rules

    rules: Optional["ProjectRules"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )


class WorkflowPolicy(BaseModel, table=True):
    """Explicit policies for workflow transitions (DoR/DoD)"""
    __tablename__ = "workflow_policies"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)
    from_status: str = Field(max_length=50, nullable=False)
    to_status: str = Field(max_length=50, nullable=False)
    criteria: dict | None = Field(default=None, sa_column=Column(JSON))
    # Example criteria: {"assignee_required": true, "acceptance_criteria_defined": true}
    required_role: str | None = Field(default=None, max_length=50)
    is_active: bool = Field(default=True, nullable=False)

    # Relationships
    project: "Project" = Relationship()


class Story(BaseModel, table=True):
    """
    Story model for Kanban board.
    Replaces BacklogItem with proper status columns: Todo, InProgress, Review, Done.
    Supports only UserStory and EnablerStory types.
    """
    __tablename__ = "stories"

    project_id: UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True
    )
    parent_id: UUID | None = Field(
        default=None, foreign_key="stories.id", ondelete="SET NULL"
    )

    # Story fields
    type: StoryType = Field(default=StoryType.USER_STORY)
    title: str
    description: str | None = Field(default=None, sa_column=Column(Text))
    status: StoryStatus = Field(default=StoryStatus.TODO)

    # Epic relationship (for linking stories to epics table)
    epic_id: UUID | None = Field(default=None, foreign_key="epics.id", ondelete="SET NULL")

    # Acceptance criteria (BA fills this)
    acceptance_criteria: str | None = Field(default=None, sa_column=Column(Text))

    # Assignment fields (TeamLeader assigns)
    assignee_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    reviewer_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )

    # Planning fields
    rank: int | None = Field(default=None)
    estimate_value: int | None = Field(default=None)
    story_point: int | None = Field(default=None)  # INVEST: Estimable (Fibonacci: 1,2,3,5,8,13)
    priority: int | None = Field(default=None)  # Legacy numeric priority

    # INVEST principle fields (for BA workflow)
    story_priority: StoryPriority | None = Field(default=None)  # High/Medium/Low
    dependencies: list = Field(default_factory=list, sa_column=Column(JSON))  # INVEST: Independent (story IDs)

    # Lifecycle fields
    pause: bool = Field(default=False)
    deadline: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Flow metrics tracking (Lean Kanban)
    started_at: datetime | None = Field(default=None)  # When moved to InProgress
    review_started_at: datetime | None = Field(default=None)  # When moved to Review

    # Token usage tracking (for AI agents)
    token_used: int | None = Field(default=None)

    # Relationships
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

    # Lean Kanban flow metrics (computed properties)
    @property
    def cycle_time_hours(self) -> float | None:
        """Cycle time: time from started (InProgress) to completed (Done)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 3600
        return None

    @property
    def lead_time_hours(self) -> float | None:
        """Lead time: time from created to completed"""
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds() / 3600
        return None

    @property
    def age_in_current_status_hours(self) -> float:
        """How long the story has been in its current status"""
        # Determine when the current status started
        status_start_time = self.created_at  # Default to creation

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


class AgentStatus(str, Enum):
    """Runtime status of an agent (unified for runtime and database)"""
    created = "created"  # Initial state when agent is instantiated
    starting = "starting"  # Agent is starting up
    running = "running"  # Agent is running (legacy, mostly uses idle/busy)
    idle = "idle"  # Agent is running and waiting for work
    busy = "busy"  # Agent is actively executing a task
    stopping = "stopping"  # Agent is shutting down
    stopped = "stopped"  # Agent has stopped cleanly
    error = "error"  # Agent encountered an error
    terminated = "terminated"  # Permanent shutdown, won't restart


class Agent(BaseModel, table=True):
    __tablename__ = "agents"

    # Project relationship - each agent belongs to a project
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    # Agent identity
    name: str  # Display name (e.g., "Mike (Developer)")
    human_name: str = Field(nullable=False)  # Natural name like "Mike", "Alice"
    role_type: str = Field(nullable=False)  # team_leader, business_analyst, developer, tester
    agent_type: str | None = Field(default=None)  # Legacy field for compatibility

    # Runtime status
    status: AgentStatus = Field(default=AgentStatus.idle)

    # Relationships
    project: "Project" = Relationship(back_populates="agents")
    messages: list["Message"] = Relationship(back_populates="agent")


class Message(BaseModel, table=True):
    __tablename__ = "messages"

    # Single-session-per-project: attach all messages to a project
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    # Author info: either user or agent (or system/tool)
    author_type: AuthorType = Field(default=AuthorType.USER, nullable=False)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="SET NULL")

    # Message payload
    content: str

    # Structured data fields for agent previews
    message_type: str = Field(default="text", nullable=True)  # "text" | "product_brief" | "product_vision" | "product_backlog"
    structured_data: dict | None = Field(default=None, sa_column=Column(JSON))  # JSON data (brief/vision/backlog)
    message_metadata: dict | None = Field(default=None, sa_column=Column(JSON))  # Message metadata (preview_id, quality_score, approved_by, etc.)

    # Relationship back to agent
    agent: Agent | None = Relationship(back_populates="messages")


class RefreshToken(BaseModel, table=True):
    __tablename__ = "refresh_tokens"

    token: str = Field(unique=True, index=True, max_length=255)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    expires_at: datetime = Field(nullable=False)
    is_revoked: bool = Field(default=False, nullable=False)

    # Token family tracking for rotation detection
    family_id: UUID = Field(nullable=False, index=True)
    parent_token_id: UUID | None = Field(default=None, foreign_key="refresh_tokens.id", ondelete="SET NULL")

    # Relationships
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

    # Relationship
    project: Project = Relationship(back_populates="rules")



# ==================== AGENT PERSISTENCE MODELS ====================


class AgentExecutionStatus(str, Enum):
    """Status of an agent execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecution(BaseModel, table=True):
    """Track agent execution runs for observability and debugging"""
    __tablename__ = "agent_executions"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    # Agent info
    agent_name: str = Field(nullable=False)
    agent_type: str = Field(nullable=False)  # TeamLeader, BusinessAnalyst, Developer, Tester

    # Execution tracking
    status: AgentExecutionStatus = Field(default=AgentExecutionStatus.PENDING)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None)

    # Context
    trigger_message_id: UUID | None = Field(default=None, foreign_key="messages.id", ondelete="SET NULL")
    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")

    # Resource usage
    token_used: int = Field(default=0)
    llm_calls: int = Field(default=0)

    # Error tracking
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    error_traceback: str | None = Field(default=None, sa_column=Column(Text))

    # Result
    result: dict | None = Field(default=None, sa_column=Column(JSON))
    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))


class AgentConversation(BaseModel, table=True):
    """Store agent-to-agent and agent-to-user conversation history"""
    __tablename__ = "agent_conversations"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)
    execution_id: UUID | None = Field(default=None, foreign_key="agent_executions.id", ondelete="CASCADE")

    # Message info
    sender_type: str = Field(nullable=False)  # "agent" or "user"
    sender_name: str = Field(nullable=False)  # Agent name or user email
    recipient_type: str | None = Field(default=None)  # "agent", "user", "broadcast"
    recipient_name: str | None = Field(default=None)

    # Message content
    message_type: str = Field(nullable=False)  # "UserRequest", "DelegateToBA", etc.
    content: str = Field(sa_column=Column(Text))
    structured_data: dict | None = Field(default=None, sa_column=Column(JSON))

    # Metadata
    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))


class AgentMetricsSnapshot(BaseModel, table=True):
    """Periodic snapshots of agent pool metrics for historical analysis"""
    __tablename__ = "agent_metrics_snapshots"

    # Snapshot metadata
    snapshot_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    pool_name: str = Field(nullable=False, index=True)

    # Agent state counts
    total_agents: int = Field(default=0)
    idle_agents: int = Field(default=0)
    busy_agents: int = Field(default=0)
    error_agents: int = Field(default=0)

    # Execution metrics (aggregated from agent_executions)
    total_executions: int = Field(default=0)
    successful_executions: int = Field(default=0)
    failed_executions: int = Field(default=0)

    # Resource usage metrics
    total_tokens: int = Field(default=0)
    total_llm_calls: int = Field(default=0)

    # Performance metrics
    avg_execution_duration_ms: float | None = Field(default=None)

    # Process metrics (multiprocessing specific)
    process_count: int = Field(default=0)
    total_capacity: int = Field(default=0)
    used_capacity: int = Field(default=0)
    utilization_percentage: float | None = Field(default=None)

    # Additional snapshot metadata
    snapshot_metadata: dict | None = Field(default=None, sa_column=Column(JSON))


class ApprovalStatus(str, Enum):
    """Status of an approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel, table=True):
    """Human-in-the-loop approval requests from agents"""
    __tablename__ = "approval_requests"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)
    execution_id: UUID | None = Field(default=None, foreign_key="agent_executions.id", ondelete="CASCADE")

    # Request info
    request_type: str = Field(nullable=False)  # "story_creation", "story_update", "epic_creation"
    agent_name: str = Field(nullable=False)

    # Proposed changes
    proposed_data: dict = Field(sa_column=Column(JSON))  # What the agent wants to do
    preview_data: dict | None = Field(default=None, sa_column=Column(JSON))  # Preview for UI
    explanation: str | None = Field(default=None, sa_column=Column(Text))  # Why the agent proposes this

    # Approval tracking
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    approved_by_user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    approved_at: datetime | None = Field(default=None)

    # User feedback
    user_feedback: str | None = Field(default=None, sa_column=Column(Text))
    modified_data: dict | None = Field(default=None, sa_column=Column(JSON))  # User modifications to proposal

    # Result tracking
    applied: bool = Field(default=False)  # Whether the approval was actually applied
    applied_at: datetime | None = Field(default=None)
    created_entity_id: UUID | None = Field(default=None)  # ID of created Story/Epic if applicable


# ==================== BUSINESS ANALYST WORKFLOW MODELS ====================


class BASessionStatus(str, Enum):
    """Status of a BA analysis session"""
    ANALYSIS = "analysis"  # Gathering requirements
    BRIEF = "brief"  # Creating Product Brief
    SOLUTION = "solution"  # Designing business flows
    BACKLOG = "backlog"  # Creating Epics & Stories
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BASession(BaseModel, table=True):
    """Track Business Analyst analysis sessions"""
    __tablename__ = "ba_sessions"

    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")

    # Session info
    status: BASessionStatus = Field(default=BASessionStatus.ANALYSIS)
    current_phase: str = Field(default="analysis")  # analysis, brief, solution, backlog

    # Conversation tracking
    conversation_history: list = Field(default_factory=list, sa_column=Column(JSON))
    turn_count: int = Field(default=0)

    # Phase transitions
    phase_transitions: list = Field(default_factory=list, sa_column=Column(JSON))

    # Completion tracking
    completed_at: datetime | None = Field(default=None)

    # Metadata
    session_metadata: dict | None = Field(default=None, sa_column=Column(JSON))

    # Relationships
    project: Project = Relationship()
    requirements: list["Requirement"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    product_brief: Optional["ProductBrief"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )
    business_flows: list["BusinessFlow"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class RequirementCategory(str, Enum):
    """Category of a requirement"""
    PROBLEM_GOALS = "problem_goals"
    USERS_STAKEHOLDERS = "users_stakeholders"
    FEATURES_SCOPE = "features_scope"


class Requirement(BaseModel, table=True):
    """Individual requirement collected during analysis"""
    __tablename__ = "requirements"

    session_id: UUID = Field(foreign_key="ba_sessions.id", nullable=False, ondelete="CASCADE", index=True)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    # Requirement details
    category: RequirementCategory = Field(nullable=False)
    content: str = Field(sa_column=Column(Text))

    # Source tracking
    extracted_from_message: str | None = Field(default=None, sa_column=Column(Text))
    turn_number: int | None = Field(default=None)

    # Relationship
    session: BASession = Relationship(back_populates="requirements")


class ProductBrief(BaseModel, table=True):
    """Product Brief document created during brief phase"""
    __tablename__ = "product_briefs"

    session_id: UUID = Field(foreign_key="ba_sessions.id", nullable=False, ondelete="CASCADE", unique=True)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    # Brief sections
    product_summary: str = Field(sa_column=Column(Text))
    problem_statement: str = Field(sa_column=Column(Text))
    target_users: str = Field(sa_column=Column(Text))
    product_goals: str = Field(sa_column=Column(Text))
    scope: str = Field(sa_column=Column(Text))

    # Versioning
    revision_count: int = Field(default=0)

    # Approval tracking
    approved: bool = Field(default=False)
    approved_at: datetime | None = Field(default=None)
    approval_feedback: str | None = Field(default=None, sa_column=Column(Text))

    # Relationship
    session: BASession = Relationship(back_populates="product_brief")


class BusinessFlow(BaseModel, table=True):
    """Business flow/user journey designed during solution phase"""
    __tablename__ = "business_flows"

    session_id: UUID = Field(foreign_key="ba_sessions.id", nullable=False, ondelete="CASCADE", index=True)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    # Flow details
    name: str
    description: str = Field(sa_column=Column(Text))
    steps: list = Field(sa_column=Column(JSON))  # List of step descriptions
    actors: list = Field(sa_column=Column(JSON))  # List of actors involved

    # Ordering
    flow_order: int | None = Field(default=None)

    # Relationship
    session: BASession = Relationship(back_populates="business_flows")

