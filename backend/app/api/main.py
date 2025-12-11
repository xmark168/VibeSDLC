from fastapi import APIRouter

from app.api.routes import (
    agent_management,  # Agent pools and monitoring
    agents,
    artifacts,  # Agent-produced artifacts (PRD, architecture, code, etc.)
    auth,
    chat,  # WebSocket chat endpoint
    files,  # Project file management
    lean_kanban,  # Lean Kanban features: WIP limits, policies, flow metrics
    linked_accounts,  # OAuth account linking
    messages,
    oauth,  # OAuth authentication
    payments,  # Payment and PayOS integration
    personas,  # Persona template management
    plans,  # Plan management
    profile,  # User profile management
    project_rules,  # Project-specific rules and configurations
    projects,
    sepay,  # SePay payment integration
    stories,  # Story management (Kanban with Todo/InProgress/Review/Done)
    tech_stacks,  # TechStack management
    two_factor,  # Two-factor authentication
    users,
    utils,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(two_factor.router)  # 2FA routes
api_router.include_router(oauth.router)  # OAuth routes
api_router.include_router(linked_accounts.router)  # Linked accounts
api_router.include_router(profile.router)  # User profile management
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(
    stories.router
)  # Story API (Kanban: Todo/InProgress/Review/Done)
api_router.include_router(projects.router)
api_router.include_router(files.router)  # Project file management
api_router.include_router(
    lean_kanban.router
)  # Lean Kanban: WIP limits, policies, metrics
api_router.include_router(messages.router)
api_router.include_router(plans.router)  # Plan management
api_router.include_router(payments.router)  # Payment and PayOS integration
api_router.include_router(sepay.router)  # SePay payment integration
api_router.include_router(personas.router)  # Persona template management
api_router.include_router(tech_stacks.router)  # TechStack management
api_router.include_router(
    agent_management.router
)  # Agent pools and monitoring - MUST be before agents.router
api_router.include_router(agents.router)
api_router.include_router(
    artifacts.router
)  # Artifact management (agent-produced documents)
api_router.include_router(
    project_rules.router
)  # Project-specific rules and configurations
api_router.include_router(chat.router)  # WebSocket chat endpoint
