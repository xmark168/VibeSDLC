from fastapi import APIRouter

from app.api.routes import (
    agent_management,
    agents,
    artifacts,
    auth,
    chat,
    files,
    kanban,
    linked_accounts,
    messages,
    oauth,
    payments,
    personas,
    plans,
    profile,
    project_rules,
    projects,
    sepay,
    stories,
    tech_stacks,
    two_factor,
    users,
)

api_router = APIRouter()

# Auth
api_router.include_router(auth.router)
api_router.include_router(two_factor.router)
api_router.include_router(oauth.router)
api_router.include_router(linked_accounts.router)
api_router.include_router(profile.router)
api_router.include_router(users.router)

# Core
api_router.include_router(projects.router)
api_router.include_router(stories.router)
api_router.include_router(messages.router)
api_router.include_router(files.router)
api_router.include_router(kanban.router)
api_router.include_router(artifacts.router)
api_router.include_router(project_rules.router)

# Agents (agent_management MUST be before agents)
api_router.include_router(agent_management.router)
api_router.include_router(agents.router)
api_router.include_router(personas.router)

# Payments
api_router.include_router(plans.router)
api_router.include_router(payments.router)
api_router.include_router(sepay.router)

# Config
api_router.include_router(tech_stacks.router)
api_router.include_router(chat.router)
