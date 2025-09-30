"""Routing for Management Service."""

from fastapi import APIRouter, Request, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.proxy import service_proxy
from app.core.security import security

router = APIRouter(prefix="/management", tags=["management"])


@router.api_route(
    "/users/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_users(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Proxy requests to Management Service users endpoints."""
    target_url = settings.get_management_service_url()
    full_path = f"/api/v1/users/{path}" if path else "/api/v1/users/"
    return await service_proxy.proxy_request(request, target_url, full_path)


@router.api_route(
    "/users",
    methods=["GET", "POST"],
)
async def proxy_users_root(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Proxy requests to Management Service users root endpoint."""
    target_url = settings.get_management_service_url()
    return await service_proxy.proxy_request(request, target_url, "/api/v1/users/")


@router.api_route(
    "/items/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_items(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Proxy requests to Management Service items endpoints."""
    target_url = settings.get_management_service_url()
    full_path = f"/api/v1/items/{path}" if path else "/api/v1/items/"
    return await service_proxy.proxy_request(request, target_url, full_path)


@router.api_route(
    "/items",
    methods=["GET", "POST"],
)
async def proxy_items_root(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Proxy requests to Management Service items root endpoint."""
    target_url = settings.get_management_service_url()
    return await service_proxy.proxy_request(request, target_url, "/api/v1/items/")


# Public endpoints (no auth required)
@router.api_route(
    "/login",
    methods=["POST"],
)
async def proxy_login(request: Request):
    """Proxy login requests to Management Service."""
    target_url = settings.get_management_service_url()
    return await service_proxy.proxy_request(request, target_url, "/api/v1/login/access-token")


@router.api_route(
    "/signup",
    methods=["POST"],
)
async def proxy_signup(request: Request):
    """Proxy signup requests to Management Service."""
    target_url = settings.get_management_service_url()
    return await service_proxy.proxy_request(request, target_url, "/api/v1/users/signup")


@router.api_route(
    "/password-recovery/{path:path}",
    methods=["POST"],
)
async def proxy_password_recovery(path: str, request: Request):
    """Proxy password recovery requests to Management Service."""
    target_url = settings.get_management_service_url()
    full_path = f"/api/v1/password-recovery/{path}"
    return await service_proxy.proxy_request(request, target_url, full_path)