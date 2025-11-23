import logging
import time
import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests."""

    def __init__(self, app):
        super().__init__(app)
        # Initialize logger in the middleware to ensure it's accessible
        self.logger = logging.getLogger("app.main.RequestLoggingMiddleware")

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            # Log incoming request
            self.logger.info(f"→ {request.method} {request.url.path}")
            # Fallback to print if logging fails
            print(f"→ {request.method} {request.url.path}", flush=True)
        except Exception as e:
            print(f"Error logging request: {e}", flush=True)

        # Process request
        response = await call_next(request)

        try:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            self.logger.info(
                f"← {request.method} {request.url.path} - "
                f"{response.status_code} - {duration_ms:.0f}ms"
            )
            # Fallback to print if logging fails
            print(
                f"← {request.method} {request.url.path} - "
                f"{response.status_code} - {duration_ms:.0f}ms",
                flush=True
            )
        except Exception as e:
            print(f"Error logging response: {e}", flush=True)

        return response


def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    return route.name


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database, create superuser
    with Session(engine) as session:
        init_db(session)

    # Ensure Kafka topics exist before starting services
    from app.kafka import ensure_kafka_topics
    try:
        topics_ok = await ensure_kafka_topics()
        if topics_ok:
            logger.info("✅ All Kafka topics verified/created")
        else:
            logger.warning("⚠️  Some Kafka topics failed to create")
    except Exception as e:
        logger.warning(f"Failed to ensure Kafka topics: {e}")
        logger.warning("Continuing anyway - topics may auto-create...")

    # Start Kafka producer
    from app.kafka import get_kafka_producer, shutdown_kafka_producer
    try:
        producer = await get_kafka_producer()
        logger.info("Kafka producer started")
    except Exception as e:
        logger.warning(f"Failed to start Kafka producer: {e}")
        logger.warning("Continuing without Kafka support...")

    # Start Central Message Router (dispatches tasks to agents)
    from app.kafka.router_service import start_router_service, stop_router_service
    try:
        await start_router_service()
        logger.info("Central Message Router started")
    except Exception as e:
        logger.warning(f"Failed to start Message Router: {e}")
        logger.warning("Continuing without router support...")

    # Start all Kafka consumers (legacy consumer registry)
    from app.kafka.consumer_registry import start_all_consumers, shutdown_all_consumers
    try:
        await start_all_consumers()
        logger.info("All Kafka consumers started")
    except Exception as e:
        logger.warning(f"Failed to start Kafka consumers: {e}")
        logger.warning("Continuing without consumer support...")

    # Initialize default agent pools (using AgentPoolManager)
    from app.api.routes.agent_management import initialize_default_pools
    try:
        await initialize_default_pools()
        logger.info("Default agent pools initialized with AgentPoolManager")
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

    # Shutdown agent pools (in-memory managers)
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

    # Shutdown Central Message Router
    try:
        await stop_router_service()
        logger.info("Central Message Router shut down")
    except Exception as e:
        logger.error(f"Error shutting down Message Router: {e}")

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

# Add middlewares in order (they execute in reverse order of addition)
# 1. Request Logging (executes last, wraps everything)
app.add_middleware(RequestLoggingMiddleware)

# 2. CORS (executes before logging)
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
