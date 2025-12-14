from fastapi import APIRouter
from app.api.routes import (
    agent_management, agents, artifacts, auth, chat, files, kanban,
    linked_accounts, messages, oauth, payments, personas, plans,
    profile, project_rules, projects, sepay, stories, tech_stacks,
    two_factor, users,
)

api_router = APIRouter()

for router in [
    auth.router, two_factor.router, oauth.router, linked_accounts.router,
    profile.router, users.router, projects.router, stories.router,
    messages.router, files.router, kanban.router, artifacts.router,
    project_rules.router, agent_management.router, agents.router,
    personas.router, plans.router, payments.router, sepay.router,
    tech_stacks.router, chat.router,
]:
    api_router.include_router(router)
