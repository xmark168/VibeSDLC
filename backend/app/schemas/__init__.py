"""Schemas package - organized by domain."""

# User schemas
from .user import (
    UserPublic,
    UserAdminPublic,
    UsersPublic,
    UsersAdminPublic,
    UserCreate,
    UserAdminCreate,
    UserLogin,
    UserUpdate,
    UserAdminUpdate,
    UserUpdateMe,
    UpdatePassword,
    UserRegister,
    BulkUserIds,
    UserStatsResponse,
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
    AgentPoolPublic,
    UpdatePoolConfigRequest,
    AgentPoolMetricsPublic,
    CreatePoolRequestExtended,
    ScalePoolRequest,
    PoolSuggestion,
    CurrentTaskInfo,
    RecentActivity,
    AgentActivityResponse,
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

# Common schemas (moved to auth.py)
from .auth import (
    Message,
    NewPassword,
)

# Kanban schemas
from .lean_kanban import (
    WIPLimitCreate,
    WIPLimitUpdate,
    WIPLimitPublic,
    WIPLimitsPublic,
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

# Persona schemas
from .persona import (
    PersonaBase,
    PersonaCreate,
    PersonaUpdate,
    PersonaResponse,
    PersonaWithUsageStats,
)

# Two-Factor Authentication schemas
from .two_factor import (
    TwoFactorSetupResponse,
    TwoFactorVerifySetupRequest,
    TwoFactorVerifySetupResponse,
    TwoFactorDisableRequest,
    TwoFactorDisableResponse,
    TwoFactorRequestDisableRequest,
    TwoFactorRequestDisableResponse,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
    TwoFactorStatusResponse,
    TwoFactorBackupCodesResponse,
    LoginRequires2FAResponse,
)

# Linked Account schemas
from .linked_account import (
    LinkedAccountPublic,
    LinkedAccountsResponse,
    LinkAccountRequest,
    UnlinkAccountRequest,
    UnlinkAccountResponse,
    LinkCallbackResponse,
    InitiateLinkResponse,
)

# Profile schemas
from .profile import (
    ProfileUpdate,
    ChangePasswordRequest,
    SetPasswordRequest,
    PasswordStatusResponse,
    PasswordChangeResponse,
    ProfileResponse,
    AvatarUploadResponse,
)

# Credits schemas
from .credits import (
    CreditActivityItem,
    CreditActivityResponse,
    TokenMonitoringStats,
)

# Agent Management schemas
from .agent_management import (
    SystemStatusResponse,
    EmergencyActionRequest,
    AgentConfigSchema,
    AgentConfigResponse,
    BulkAgentRequest,
    BulkSpawnRequest,
    BulkOperationResponse,
    ScalingTriggerType,
    ScalingAction,
    AutoScalingRule,
    AutoScalingRuleCreate,
    AgentTokenStats,
    PoolTokenStats,
    SystemTokenSummary,
)

# Artifacts schemas
from .artifacts import (
    ArtifactResponse,
    ArtifactListResponse,
    UpdateArtifactStatusRequest,
)

# Story additional schemas
from .story import (
    ReviewActionType,
    ReviewActionRequest,
)

__all__ = [
    # User
    "UserPublic",
    "UserAdminPublic",
    "UsersPublic",
    "UsersAdminPublic",
    "UserCreate",
    "UserAdminCreate",
    "UserLogin",
    "UserUpdate",
    "UserAdminUpdate",
    "UserUpdateMe",
    "UpdatePassword",
    "UserRegister",
    "BulkUserIds",
    "UserStatsResponse",
    
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
    "AgentPoolPublic",
    "UpdatePoolConfigRequest",
    "AgentPoolMetricsPublic",
    "CreatePoolRequestExtended",
    "ScalePoolRequest",
    "PoolSuggestion",
    "CurrentTaskInfo",
    "RecentActivity",
    "AgentActivityResponse",
    
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
    
    # Kanban
    "WIPLimitCreate",
    "WIPLimitUpdate",
    "WIPLimitPublic",
    "WIPLimitsPublic",
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

    # Persona
    "PersonaBase",
    "PersonaCreate",
    "PersonaUpdate",
    "PersonaResponse",
    "PersonaWithUsageStats",
    "UpdateAutoRenew",
    
    # Two-Factor Authentication
    "TwoFactorSetupResponse",
    "TwoFactorVerifySetupRequest",
    "TwoFactorVerifySetupResponse",
    "TwoFactorDisableRequest",
    "TwoFactorDisableResponse",
    "TwoFactorRequestDisableRequest",
    "TwoFactorRequestDisableResponse",
    "TwoFactorVerifyRequest",
    "TwoFactorVerifyResponse",
    "TwoFactorStatusResponse",
    "TwoFactorBackupCodesResponse",
    "LoginRequires2FAResponse",
    
    # Linked Account
    "LinkedAccountPublic",
    "LinkedAccountsResponse",
    "LinkAccountRequest",
    "UnlinkAccountRequest",
    "UnlinkAccountResponse",
    "LinkCallbackResponse",
    "InitiateLinkResponse",
    
    # Profile
    "ProfileUpdate",
    "ChangePasswordRequest",
    "SetPasswordRequest",
    "PasswordStatusResponse",
    "PasswordChangeResponse",
    "ProfileResponse",
    "AvatarUploadResponse",
    
    # Credits
    "CreditActivityItem",
    "CreditActivityResponse",
    "TokenMonitoringStats",
    
    # Agent Management
    "SystemStatusResponse",
    "EmergencyActionRequest",
    "AgentConfigSchema",
    "AgentConfigResponse",
    "BulkAgentRequest",
    "BulkSpawnRequest",
    "BulkOperationResponse",
    "ScalingTriggerType",
    "ScalingAction",
    "AutoScalingRule",
    "AutoScalingRuleCreate",
    "AgentTokenStats",
    "PoolTokenStats",
    "SystemTokenSummary",
    
    # Artifacts
    "ArtifactResponse",
    "ArtifactListResponse",
    "UpdateArtifactStatusRequest",
    
    # Story (additional)
    "ReviewActionType",
    "ReviewActionRequest",
]
