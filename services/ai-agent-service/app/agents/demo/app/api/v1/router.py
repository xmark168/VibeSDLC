"""
Main API router for version 1.
Includes all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

api_router.include_router(users.router, prefix="/users", tags=["users"])
