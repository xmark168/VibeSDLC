from fastapi import APIRouter

from app.api.routes import (
    agent_management,  # Agent pools and monitoring
    agents,
    artifacts,  # Agent-produced artifacts (PRD, architecture, code, etc.)
    auth,
    chat,  # WebSocket chat endpoint
    files,  # Project file management
    lean_kanban,  # Lean Kanban features: WIP limits, policies, flow metrics
    messages,
    project_rules,  # Project-specific rules and configurations
    projects,
    stories,  # Story management (Kanban with Todo/InProgress/Review/Done)
    users,
    utils
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(stories.router)  # Story API (Kanban: Todo/InProgress/Review/Done)
api_router.include_router(projects.router)
api_router.include_router(files.router)  # Project file management
api_router.include_router(lean_kanban.router)  # Lean Kanban: WIP limits, policies, metrics
api_router.include_router(messages.router)
api_router.include_router(agent_management.router)  # Agent pools and monitoring - MUST be before agents.router
api_router.include_router(agents.router)
api_router.include_router(artifacts.router)  # Artifact management (agent-produced documents)
api_router.include_router(project_rules.router)  # Project-specific rules and configurations
api_router.include_router(chat.router)  # WebSocket chat endpoint
