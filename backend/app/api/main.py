from fastapi import APIRouter

from app.api.routes import (
    auth,
    private,
    users,
    utils,
    backlog_items,
    projects,
    messages,
    agents,
    github_webhook,
    github_repositories,
    github_create_repo,
    blockers,  # TraDS: Sprint Retrospective Blockers
    project_rules,  # TraDS: Sprint Retrospective Project Rules
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(backlog_items.router)
api_router.include_router(projects.router)
api_router.include_router(messages.router)
api_router.include_router(agents.router)
api_router.include_router(github_webhook.router)
api_router.include_router(github_repositories.router)
api_router.include_router(github_create_repo.router)
api_router.include_router(blockers.router)  # TraDS: Sprint Retrospective Blockers
api_router.include_router(project_rules.router)  # TraDS: Sprint Retrospective Project Rules

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
