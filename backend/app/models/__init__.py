"""
Models package - All SQLModel/SQLAlchemy models for VibeSDLC.

Import order matters for foreign key dependencies:
1. base (enums, BaseModel)
2. user (no FK dependencies on other models)
3. agent (AgentPool before Project due to FK)
4. project (depends on Agent)
5. story (depends on Project, Agent)
6. message (depends on Agent)
7. execution (depends on various)
8. artifact (depends on various)
9. billing (depends on User, Agent)
"""

# Re-export SQLModel for alembic compatibility
from sqlmodel import SQLModel

# Base model and enums
from app.models.base import (
    BaseModel,
    Role,
    LimitType,
    StoryStatus,
    StoryAgentState,
    StoryType,
    AuthorType,
    MessageVisibility,
    AgentStatus,
    PoolType,
    EpicStatus,
    AgentExecutionStatus,
    QuestionType,
    QuestionStatus,
    ArtifactType,
    ArtifactStatus,
    OrderType,
    OrderStatus,
    InvoiceStatus,
)

# User models
from app.models.user import User, RefreshToken, OAuthProvider, LinkedAccount

# AgentPool models (must be before Agent due to FK)
from app.models.agent_pool import (
    AgentPool,
    AgentPoolMetrics,
)

# Agent models (before Project due to FK dependencies)
from app.models.agent import (
    AgentPersonaTemplate,
    Agent,
)

# Project models
from app.models.project import (
    Project,
    WorkflowPolicy,
    ProjectRules,
    ProjectPreference,
)

# Story models
from app.models.story import (
    Epic,
    Story,
    Comment,
    IssueActivity,
)

# Message models
from app.models.message import (
    Message,
    AgentConversation,
)

# Execution models
from app.models.execution import (
    AgentExecution,
    AgentMetricsSnapshot,
    AgentQuestion,
)

# Artifact models
from app.models.artifact import Artifact

# Billing models
from app.models.billing import (
    Plan,
    Subscription,
    CreditWallet,
    CreditActivity,
    Order,
    Invoice,
)

__all__ = [
    # SQLModel for alembic
    "SQLModel",
    # Base
    "BaseModel",
    "Role",
    "LimitType",
    "StoryStatus",
    "StoryAgentState",
    "StoryType",
    "AuthorType",
    "MessageVisibility",
    "AgentStatus",
    "PoolType",
    "EpicStatus",
    "AgentExecutionStatus",
    "QuestionType",
    "QuestionStatus",
    "ArtifactType",
    "ArtifactStatus",
    "OrderType",
    "OrderStatus",
    "InvoiceStatus",
    # User
    "User",
    "RefreshToken",
    "OAuthProvider",
    "LinkedAccount",
    # Agent
    "AgentPersonaTemplate",
    "AgentPool",
    "AgentPoolMetrics",
    "Agent",
    # Project
    "Project",
    "WorkflowPolicy",
    "ProjectRules",
    "ProjectPreference",
    # Story
    "Epic",
    "Story",
    "Comment",
    "IssueActivity",
    # Message
    "Message",
    "AgentConversation",
    # Execution
    "AgentExecution",
    "AgentMetricsSnapshot",
    "AgentQuestion",
    # Artifact
    "Artifact",
    # Billing
    "Plan",
    "Subscription",
    "CreditWallet",
    "CreditActivity",
    "Order",
    "Invoice",
]
