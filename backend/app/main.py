import asyncio
import logging
import os

import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import init_db, engine
from app.core.logging_config import setup_logging

# Ensure uploads directory exists
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
AVATARS_DIR = os.path.join(UPLOADS_DIR, "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)

setup_logging()
logger = logging.getLogger(__name__)

def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    return route.name


@asynccontextmanager
async def lifespan(app: FastAPI):
    with Session(engine) as session:
        init_db(session)

    from app.kafka import ensure_kafka_topics
    try:
        topics_ok = await ensure_kafka_topics()
        if not topics_ok:
            logger.warning("⚠️  Some Kafka topics failed to create")
    except Exception as e:
        logger.warning(f"Failed to ensure Kafka topics: {e}")

    from app.agents.core.router import start_router_service, stop_router_service
    try:
        await start_router_service()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start Message Router: {e}")

    from app.kafka.consumer_registry import start_all_consumers, shutdown_all_consumers
    try:
        await start_all_consumers()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start Kafka consumers: {e}")

    from app.api.routes.agent_management import initialize_default_pools
    try:
        await initialize_default_pools()
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize agent pools: {e}")

    from app.agents.core import get_agent_monitor
    try:
        monitor = get_agent_monitor()
        await monitor.start(monitor_interval=30)
    except Exception as e:
        logger.warning(f"⚠️ Failed to start monitoring: {e}")

    from app.websocket.activity_buffer import activity_buffer
    try:
        await activity_buffer.start()
    except Exception as e:
        logger.warning(f"Failed to start activity buffer: {e}")

    from app.websocket.kafka_bridge import websocket_kafka_bridge
    try:
        await websocket_kafka_bridge.start()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start WebSocket bridge: {e}")

    yield

    try:
        try:
            await websocket_kafka_bridge.stop()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error stopping WebSocket bridge: {e}")
        
        try:
            await activity_buffer.stop()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error stopping activity buffer: {e}")

        try:
            monitor = get_agent_monitor()
            await monitor.stop()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error shutting down monitoring system: {e}")

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

        try:
            await stop_router_service()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error shutting down Message Router: {e}")
    
    except (KeyboardInterrupt, asyncio.CancelledError):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
