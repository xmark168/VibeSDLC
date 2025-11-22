import logging
import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import init_db, engine
from app.core.logging_config import setup_logging
from sqlmodel import Session

# Initialize logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    return route.name


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database, create superuser
    with Session(engine) as session:
        init_db(session)

    # Start Kafka producer
    from app.kafka import get_kafka_producer, shutdown_kafka_producer
    try:
        producer = await get_kafka_producer()
        logger.info("Kafka producer started")
    except Exception as e:
        logger.warning(f"Failed to start Kafka producer: {e}")
        logger.warning("Continuing without Kafka support...")

    # Start all Kafka consumers (legacy consumer registry)
    from app.kafka.consumer_registry import start_all_consumers, shutdown_all_consumers
    try:
        await start_all_consumers()
        logger.info("All Kafka consumers started")
    except Exception as e:
        logger.warning(f"Failed to start Kafka consumers: {e}")
        logger.warning("Continuing without consumer support...")

    # Start Agent Orchestrator (manages all crew consumers)
    from app.agents.orchestrator import start_orchestrator, stop_orchestrator
    try:
        await start_orchestrator()
        logger.info("Agent Orchestrator started - all crews ready")
    except Exception as e:
        logger.warning(f"Failed to start Agent Orchestrator: {e}")
        logger.warning("Continuing without agent support...")

    # Initialize default agent pools
    from app.api.routes.agent_management import initialize_default_pools
    try:
        await initialize_default_pools()
        logger.info("Default agent pools initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize agent pools: {e}")
        logger.warning("Continuing without agent pools...")

    # Start agent monitoring system
    from app.agents.core import get_agent_monitor
    try:
        monitor = get_agent_monitor()
        await monitor.start(monitor_interval=30)
        logger.info("Agent monitoring system started")
    except Exception as e:
        logger.warning(f"Failed to start monitoring system: {e}")
        logger.warning("Continuing without monitoring system...")

    # Start WebSocket-Kafka bridge
    from app.websocket.kafka_bridge import websocket_kafka_bridge
    try:
        await websocket_kafka_bridge.start()
        logger.info("WebSocket-Kafka bridge started")
    except Exception as e:
        logger.warning(f"Failed to start WebSocket-Kafka bridge: {e}")
        logger.warning("Continuing without WebSocket bridge...")

    yield

    # Shutdown: cleanup consumers and producer
    logger.info("Shutting down...")

    try:
        await websocket_kafka_bridge.stop()
        logger.info("WebSocket-Kafka bridge shut down")
    except Exception as e:
        logger.error(f"Error shutting down WebSocket-Kafka bridge: {e}")

    # Shutdown agent monitoring system
    try:
        monitor = get_agent_monitor()
        await monitor.stop()
        logger.info("Agent monitoring system shut down")
    except Exception as e:
        logger.error(f"Error shutting down monitoring system: {e}")

    # Shutdown agent pools
    from app.api.routes.agent_management import _pool_registry
    try:
        for pool_name, pool in list(_pool_registry.items()):
            await pool.stop(graceful=True)
            logger.info(f"Pool '{pool_name}' shut down")
        _pool_registry.clear()
        logger.info("All agent pools shut down")
    except Exception as e:
        logger.error(f"Error shutting down agent pools: {e}")

    try:
        await stop_orchestrator()
        logger.info("Agent Orchestrator shut down")
    except Exception as e:
        logger.error(f"Error shutting down orchestrator: {e}")

    try:
        await shutdown_all_consumers()
        logger.info("Kafka consumers shut down")
    except Exception as e:
        logger.error(f"Error shutting down consumers: {e}")

    try:
        await shutdown_kafka_producer()
        logger.info("Kafka producer shut down")
    except Exception as e:
        logger.error(f"Error shutting down producer: {e}")

    logger.info("Application shutdown complete")


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)



app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Add rate limiter to app state

# CORS temporarily disabled for WebSocket debugging
app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# SlowAPI middleware temporarily disabled for debugging
# app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)
