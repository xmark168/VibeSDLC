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

    # Initialize default agent pools (now handles agent lifecycle - orchestrator removed)
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

    # Start metrics collector for analytics
    from app.tasks import start_metrics_collector
    try:
        await start_metrics_collector(interval_seconds=300, retention_days=30)
        logger.info("Metrics collector started (5-minute intervals, 30-day retention)")
    except Exception as e:
        logger.warning(f"Failed to start metrics collector: {e}")
        logger.warning("Continuing without metrics collection...")

    yield

    # Shutdown: cleanup consumers and producer
    logger.info("Shutting down...")

    try:
        await websocket_kafka_bridge.stop()
        logger.info("WebSocket-Kafka bridge shut down")
    except Exception as e:
        logger.error(f"Error shutting down WebSocket-Kafka bridge: {e}")

    # Shutdown metrics collector
    from app.tasks import stop_metrics_collector
    try:
        await stop_metrics_collector()
        logger.info("Metrics collector shut down")
    except Exception as e:
        logger.error(f"Error shutting down metrics collector: {e}")

    # Shutdown agent monitoring system
    try:
        monitor = get_agent_monitor()
        await monitor.stop()
        logger.info("Agent monitoring system shut down")
    except Exception as e:
        logger.error(f"Error shutting down monitoring system: {e}")

    # Shutdown agent pools (multiprocessing managers)
    from app.api.routes.agent_management import _manager_registry
    try:
        for pool_name, manager in list(_manager_registry.items()):
            await manager.stop(graceful=True)
            logger.info(f"Pool manager '{pool_name}' shut down")
        _manager_registry.clear()
        logger.info("All agent pool managers shut down")
    except Exception as e:
        logger.error(f"Error shutting down agent pools: {e}")

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
