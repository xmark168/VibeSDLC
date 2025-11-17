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
    blockers,  # TraDS: Sprint Retrospective Blockers
    project_rules,  # TraDS: Sprint Retrospective Project Rules
    crews,  # CrewAI multi-agent system
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
api_router.include_router(blockers.router)  # TraDS: Sprint Retrospective Blockers
api_router.include_router(project_rules.router)  # TraDS: Sprint Retrospective Project Rules
api_router.include_router(crews.router)  # CrewAI multi-agent system

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
