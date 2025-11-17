from fastapi import APIRouter

from app.api.routes import (
    auth,
    private,
    users,
    utils,
    stories,  # Story management (Kanban with Todo/InProgress/Review/Done)
    projects,
    messages,
    agents,
    blockers,  # Story blockers tracking
    project_rules,  # Project-specific rules and configurations
    crews,  # CrewAI multi-agent system
    chat,  # WebSocket chat endpoint
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(stories.router)  # Story API (Kanban: Todo/InProgress/Review/Done)
api_router.include_router(projects.router)
api_router.include_router(messages.router)
api_router.include_router(agents.router)
api_router.include_router(blockers.router)  # Story blockers tracking
api_router.include_router(project_rules.router)  # Project-specific rules and configurations
api_router.include_router(crews.router)  # CrewAI multi-agent system
api_router.include_router(chat.router)  # WebSocket chat endpoint

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
