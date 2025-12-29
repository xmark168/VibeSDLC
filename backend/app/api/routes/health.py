"""Health check endpoint for monitoring and load balancers."""

from fastapi import APIRouter, status
from sqlmodel import Session, select, text
from datetime import datetime
from typing import Dict, Any

from app.core.db import engine
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Returns 200 OK if service is running.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check - verifies all dependencies are available.
    Returns 200 if ready to accept traffic, 503 if not ready.
    """
    checks = {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check database connection
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        checks["checks"]["database"] = "healthy"
    except Exception as e:
        checks["checks"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "not_ready"
    
    # Check Redis connection
    try:
        from app.services.singletons import get_redis_service
        redis = get_redis_service()
        await redis.ping()
        checks["checks"]["redis"] = "healthy"
    except Exception as e:
        checks["checks"]["redis"] = f"unhealthy: {str(e)}"
        checks["status"] = "not_ready"
    
    # Return 503 if any check failed
    if checks["status"] == "not_ready":
        return checks, status.HTTP_503_SERVICE_UNAVAILABLE
    
    return checks


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check - verifies service is alive.
    Returns 200 if alive, used by Kubernetes/Docker.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
