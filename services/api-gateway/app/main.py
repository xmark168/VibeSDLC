"""API Gateway main application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.proxy import service_proxy
from app.routes import management, agents

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def custom_generate_unique_id(route: APIRoute) -> str:
    """Generate unique ID for API routes."""
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting API Gateway...")
    yield
    # Shutdown
    logger.info("Shutting down API Gateway...")
    await service_proxy.close()


app = FastAPI(
    title="VibeSDLC API Gateway",
    description="API Gateway for VibeSDLC microservices architecture",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(management.router, prefix=settings.API_V1_STR)
app.include_router(agents.router, prefix=settings.API_V1_STR)


@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    """API Gateway health check."""
    # Check downstream services
    management_health = await service_proxy.health_check(
        settings.get_management_service_url()
    )
    agent_health = await service_proxy.health_check(
        settings.get_ai_agent_service_url()
    )

    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
        "downstream_services": {
            "management_service": management_health,
            "ai_agent_service": agent_health,
        }
    }


@app.get("/")
async def root():
    """API Gateway root endpoint."""
    return {
        "message": "VibeSDLC API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )