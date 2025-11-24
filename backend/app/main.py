import asyncio
import logging
import time
import sentry_sdk
from fastapi import FastAPI, Request
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

    # Ensure Kafka topics exist before starting services
    from app.kafka import ensure_kafka_topics
    try:
        topics_ok = await ensure_kafka_topics()
        if not topics_ok:
            logger.warning("⚠️  Some Kafka topics failed to create")
    except Exception as e:
        logger.warning(f"Failed to ensure Kafka topics: {e}")

    # Start Kafka producer
    from app.kafka import get_kafka_producer, shutdown_kafka_producer
    try:
        producer = await get_kafka_producer()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start Kafka producer: {e}")

    # Start Central Message Router (dispatches tasks to agents)
    from app.agents.core.router import start_router_service, stop_router_service
    try:
        await start_router_service()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start Message Router: {e}")

    # Start all Kafka consumers (legacy consumer registry)
    from app.kafka.consumer_registry import start_all_consumers, shutdown_all_consumers
    try:
        await start_all_consumers()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start Kafka consumers: {e}")

    # Initialize default agent pools (using AgentPoolManager)
    from app.api.routes.agent_management import initialize_default_pools
    try:
        await initialize_default_pools()
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize agent pools: {e}")

    # Start agent monitoring system
    from app.agents.core import get_agent_monitor
    try:
        monitor = get_agent_monitor()
        await monitor.start(monitor_interval=30)
    except Exception as e:
        logger.warning(f"⚠️ Failed to start monitoring: {e}")

    # Start optimized WebSocket manager
    from app.websocket.manager import websocket_manager
    try:
        await websocket_manager.start()
    except Exception as e:
        logger.warning(f"Failed to start WebSocket manager: {e}")
    
    # Start activity buffer for batched DB writes
    from app.websocket.activity_buffer import activity_buffer
    try:
        await activity_buffer.start()
    except Exception as e:
        logger.warning(f"Failed to start activity buffer: {e}")

    # Start WebSocket-Kafka bridge (for backward compatibility)
    from app.websocket.kafka_bridge import websocket_kafka_bridge
    try:
        await websocket_kafka_bridge.start()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start WebSocket bridge: {e}")

    # Start metrics collector for analytics
    from app.tasks import start_metrics_collector
    try:
        await start_metrics_collector(interval_seconds=300, retention_days=30)
    except Exception as e:
        logger.warning(f"⚠️ Failed to start metrics collector: {e}")

    yield

    # Shutdown

    try:
        # Shutdown optimized WebSocket manager
        try:
            await websocket_manager.stop()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error stopping WebSocket manager: {e}")
        
        try:
            await websocket_kafka_bridge.stop()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error stopping WebSocket bridge: {e}")
        
        # Shutdown activity buffer
        try:
            await activity_buffer.stop()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error stopping activity buffer: {e}")

        # Shutdown metrics collector
        from app.tasks import stop_metrics_collector
        try:
            await stop_metrics_collector()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error stopping metrics collector: {e}")

        # Shutdown agent monitoring system
        try:
            monitor = get_agent_monitor()
            await monitor.stop()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error shutting down monitoring system: {e}")

        # Shutdown agent pools (in-memory managers)
        from app.api.routes.agent_management import _manager_registry
        try:
            for pool_name, manager in list(_manager_registry.items()):
                try:
                    await manager.stop(graceful=True)
                except (Exception, asyncio.CancelledError) as e:
                    logger.error(f"Error stopping pool '{pool_name}': {e}")
            _manager_registry.clear()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error shutting down agent pools: {e}")

        try:
            await shutdown_all_consumers()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error shutting down consumers: {e}")

        # Shutdown Central Message Router
        try:
            await stop_router_service()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error shutting down Message Router: {e}")

        try:
            await shutdown_kafka_producer()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error shutting down producer: {e}")
    
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Gracefully handle interruption during shutdown
        pass
    except Exception as e:
        logger.error(f"Unexpected error during shutdown: {e}")


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
# CORS middleware
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
