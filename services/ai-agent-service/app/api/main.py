from fastapi import APIRouter

from app.api.routes import (
    auth,
    private,
    users,
    utils,
    backlog_items,
    projects,
    sprints,
    messages,
    agents,
    chat_ws,
    agent_execution,
    github_webhook,
    github_repositories,
    github_create_repo,
    scrum_master_test,  # TraDS: Test endpoint for Sprint Planner
    blockers,  # TraDS: Sprint Retrospective Blockers
    project_rules,  # TraDS: Sprint Retrospective Project Rules
    retro_coordinator,  # TraDS: Sprint Retrospective Agent
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(backlog_items.router)
api_router.include_router(projects.router)
api_router.include_router(sprints.router)
api_router.include_router(messages.router)
api_router.include_router(agents.router)
api_router.include_router(chat_ws.router)
api_router.include_router(agent_execution.router)
api_router.include_router(github_webhook.router)
api_router.include_router(github_repositories.router)
api_router.include_router(github_create_repo.router)
api_router.include_router(scrum_master_test.router)  # TraDS: Test endpoint for Sprint Planner
api_router.include_router(blockers.router)  # TraDS: Sprint Retrospective Blockers
api_router.include_router(project_rules.router)  # TraDS: Sprint Retrospective Project Rules
api_router.include_router(retro_coordinator.router)  # TraDS: Sprint Retrospective Agent

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
