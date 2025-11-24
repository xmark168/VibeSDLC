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
    StoryUpdate,
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
    "StoryUpdate",
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
]
