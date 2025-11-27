"""Schemas package - organized by domain."""

# User schemas
from .user import (
    UserPublic,
    UsersPublic,
    UserCreate,
    UserLogin,
    UserUpdate,
    UserUpdateMe,
    UpdatePassword,
    UserRegister,
)

# Auth schemas
from .auth import (
    Token,
    TokenData,
    TokenPayload,
    RefreshTokenRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ConfirmCodeRequest,
    ConfirmCodeResponse,
    ResendCodeRequest,
    ResendCodeResponse,
    RefreshTokenResponse,
    LogoutResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)

# Message schemas
from .message import (
    ChatMessageBase,
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatMessagePublic,
    ChatMessagesPublic,
)

# Project schemas
from .project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectPublic,
    ProjectsPublic,
)

# Agent schemas (includes pool management)
from .agent import (
    AgentBase,
    AgentCreate,
    AgentUpdate,
    AgentPublic,
    AgentsPublic,
    PoolConfigSchema,
    CreatePoolRequest,
    SpawnAgentRequest,
    TerminateAgentRequest,
    PoolResponse,
    SystemStatsResponse,
)

# Story schemas
from .story import (
    StoryBase,
    StoryCreate,
    StoryUpdate,
    StoryPublic,
    StoriesPublic,
)

# File schemas
from .file import (
    FileNode,
    FileTreeResponse,
    FileContentResponse,
    GitStatusResponse,
)

# Project rules schemas
from .project_rules import (
    ProjectRulesCreate,
    ProjectRulesUpdate,
    ProjectRulesPublic,
)

# Common schemas
from .common import (
    Message,
    NewPassword,
)

# Lean Kanban schemas
from .lean_kanban import (
    WIPLimitCreate,
    WIPLimitUpdate,
    WIPLimitPublic,
    WIPLimitsPublic,
    WorkflowPolicyCreate,
    WorkflowPolicyUpdate,
    WorkflowPolicyPublic,
    WorkflowPoliciesPublic,
    StoryFlowMetrics,
    ProjectFlowMetrics,
    WIPViolation,
)

# Plan schemas
from .plan import (
    PlanBase,
    PlanCreate,
    PlanUpdate,
    PlanPublic,
    PlansPublic,
)

# Payment schemas
from .payment import (
    PaymentItemData,
    CreatePaymentRequest,
    CreateCreditPurchaseRequest,
    PaymentLinkResponse,
    PaymentStatusResponse,
    PayOSWebhookData,
    WebhookRequest,
)

# Subscription schemas
from .subscription import (
    SubscriptionPublic,
    CreditWalletPublic,
    UserSubscriptionResponse,
    UpdateAutoRenew,
)

__all__ = [
    # User
    "UserPublic",
    "UsersPublic",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserUpdateMe",
    "UpdatePassword",
    "UserRegister",
    
    # Auth
    "Token",
    "TokenData",
    "TokenPayload",
    "RefreshTokenRequest",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "ConfirmCodeRequest",
    "ConfirmCodeResponse",
    "ResendCodeRequest",
    "ResendCodeResponse",
    "RefreshTokenResponse",
    "LogoutResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    
    # Message
    "ChatMessageBase",
    "ChatMessageCreate",
    "ChatMessageUpdate",
    "ChatMessagePublic",
    "ChatMessagesPublic",
    
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectPublic",
    "ProjectsPublic",
    
    # Agent
    "AgentBase",
    "AgentCreate",
    "AgentUpdate",
    "AgentPublic",
    "AgentsPublic",
    "PoolConfigSchema",
    "CreatePoolRequest",
    "SpawnAgentRequest",
    "TerminateAgentRequest",
    "PoolResponse",
    "SystemStatsResponse",
    
    # Story
    "StoryBase",
    "StoryCreate",
    "StoryUpdate",
    "StoryPublic",
    "StoriesPublic",
    
    # File
    "FileNode",
    "FileTreeResponse",
    "FileContentResponse",
    "GitStatusResponse",
    
    # Project Rules
    "ProjectRulesCreate",
    "ProjectRulesUpdate",
    "ProjectRulesPublic",
    
    # Common
    "Message",
    "NewPassword",
    
    # Lean Kanban
    "WIPLimitCreate",
    "WIPLimitUpdate",
    "WIPLimitPublic",
    "WIPLimitsPublic",
    "WorkflowPolicyCreate",
    "WorkflowPolicyUpdate",
    "WorkflowPolicyPublic",
    "WorkflowPoliciesPublic",
    "StoryFlowMetrics",
    "ProjectFlowMetrics",
    "WIPViolation",

    # Plan
    "PlanBase",
    "PlanCreate",
    "PlanUpdate",
    "PlanPublic",
    "PlansPublic",

    # Payment
    "PaymentItemData",
    "CreatePaymentRequest",
    "CreateCreditPurchaseRequest",
    "PaymentLinkResponse",
    "PaymentStatusResponse",
    "PayOSWebhookData",
    "WebhookRequest",

    # Subscription
    "SubscriptionPublic",
    "CreditWalletPublic",
    "UserSubscriptionResponse",
    "UpdateAutoRenew",
]
