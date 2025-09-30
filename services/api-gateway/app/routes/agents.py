"""Routing for AI Agent Service."""

from fastapi import APIRouter, Request, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.proxy import service_proxy
from app.core.security import security

router = APIRouter(prefix="/agents", tags=["agents"])


@router.api_route(
    "/analyze-task",
    methods=["POST"],
)
async def proxy_analyze_task(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Proxy task analysis requests to AI Agent Service."""
    target_url = settings.get_ai_agent_service_url()
    return await service_proxy.proxy_request(request, target_url, "/api/v1/agents/analyze-task")


@router.api_route(
    "/health",
    methods=["GET"],
)
async def proxy_agent_health(request: Request):
    """Proxy health check requests to AI Agent Service."""
    target_url = settings.get_ai_agent_service_url()
    return await service_proxy.proxy_request(request, target_url, "/api/v1/agents/health")


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_agents_fallback(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Proxy other agent requests to AI Agent Service."""
    target_url = settings.get_ai_agent_service_url()
    full_path = f"/api/v1/agents/{path}"
    return await service_proxy.proxy_request(request, target_url, full_path)