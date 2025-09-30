import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.config import settings
from app.events.consumer import event_consumer
from app.agents.api import router as agents_router


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Startup
    logging.info("Starting AI Agent Service...")

    # Start Kafka consumer (will fail gracefully if Kafka is not available)
    try:
        # Don't await start() - it's a blocking consumer loop
        # Instead, we'll start it as a background task
        import asyncio
        asyncio.create_task(event_consumer.start())
        logging.info("Kafka consumer started in background")
    except Exception as e:
        logging.warning(f"Kafka consumer not started: {e}. Service will work without event processing.")

    yield

    # Shutdown
    logging.info("Shutting down AI Agent Service...")
    try:
        await event_consumer.stop()
        logging.info("Kafka consumer stopped")
    except Exception as e:
        logging.warning(f"Error stopping Kafka consumer: {e}")


app = FastAPI(
    title="AI Agent Service",
    description="AI Agent service with LangChain, LangGraph, and LangFuse integration",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Include routers
app.include_router(agents_router, prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ai-agent-service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )