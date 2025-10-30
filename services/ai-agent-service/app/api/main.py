from fastapi import APIRouter

from app.api.routes import login, private, users, utils, backlog_items, projects, sprints, messages, agents, chat_ws, agent_execution
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(backlog_items.router)
api_router.include_router(projects.router)
api_router.include_router(sprints.router)
api_router.include_router(messages.router)
api_router.include_router(agents.router)
api_router.include_router(chat_ws.router)
api_router.include_router(agent_execution.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
