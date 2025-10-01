import logging

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.config import settings
from app.agents.api import router as agents_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    title="AI Agent Service",
    description="AI Agent service with LangChain, LangGraph, and LangFuse integration",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Include routers
app.include_router(agents_router, prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", 
            "service": "ai-agent-service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )