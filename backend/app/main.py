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


async def cleanup_stale_story_states():
    """Reset stale story states on backend restart."""
    from sqlmodel import Session, text

    
    try:
        with Session(engine) as session:
            # Find stories with stale states (any non-finished state)
            stale_stories = session.exec(
                text("""
                    SELECT id, checkpoint_thread_id, worktree_path, branch_name, project_id, status
                    FROM stories 
                    WHERE agent_state IN ('PENDING', 'PROCESSING', 'PAUSED', 'CANCEL_REQUESTED')
                """)
            ).all()
            
            if not stale_stories:
                logger.info("✓ No stale story states to cleanup")
                return
            
            story_ids = [str(s[0]) for s in stale_stories]
            
            # Count stories by status for logging
            status_counts = {}
            for story in stale_stories:
                status = story[5]  # status is 6th field
                status_counts[status] = status_counts.get(status, 0) + 1
            
            logger.info(f"🧹 Cleaning up {len(stale_stories)} stale stories: {story_ids}")
            logger.info(f"   Status breakdown: {status_counts}")
            
            # Step 1: Cleanup workspaces (worktree + branch)
            from app.utils.workspace_utils import cleanup_workspace
            from app.models import Project
            from pathlib import Path
            
            cleanup_count = 0
            for story in stale_stories:
                story_id, _, worktree_path, branch_name, project_id = story
                
                # Check if worktree exists
                if worktree_path and Path(worktree_path).exists():
                    try:
                        # Get project repo path
                        project = session.get(Project, project_id)
                        if project and project.repo_path:
                            # Cleanup worktree + branch
                            cleanup_workspace(
                                repo_path=project.repo_path,
                                worktree_path=worktree_path,
                                branch_name=branch_name
                            )
                            cleanup_count += 1
                            logger.debug(f"Cleaned workspace for story {story_id}")
                    except Exception as e:
                        # Non-critical - continue cleanup
                        logger.warning(f"Failed to cleanup workspace for story {story_id}: {e}")
            
            if cleanup_count > 0:
                logger.info(f"✓ Cleaned {cleanup_count} workspaces")
            
            # Step 2: Prepare checkpoint IDs for clearing
            checkpoint_ids = [s[1] for s in stale_stories if s[1]]
            
            # Step 3: Move incomplete stories to Todo and reset agent_state
            session.exec(
                text("""
                    UPDATE stories 
                    SET status = 'Todo',
                        agent_state = NULL,
                        checkpoint_thread_id = NULL,
                        assigned_agent_id = NULL,
                        worktree_path = NULL,
                        branch_name = NULL
                    WHERE agent_state IN ('PENDING', 'PROCESSING', 'PAUSED', 'CANCEL_REQUESTED')
                """)
            )
            
            # Step 4: Clear checkpoint data
            if checkpoint_ids:
                for tid in checkpoint_ids:
                    try:
                        session.exec(text("DELETE FROM checkpoint_writes WHERE thread_id = :tid"), {"tid": tid})
                        session.exec(text("DELETE FROM checkpoint_blobs WHERE thread_id = :tid"), {"tid": tid})
                        session.exec(text("DELETE FROM checkpoints WHERE thread_id = :tid"), {"tid": tid})
                    except Exception as e:
                        logger.warning(f"Failed to delete checkpoint {tid}: {e}")
            
            session.commit()
            logger.info(
                f"✓ Moved {len(stale_stories)} incomplete stories to Todo, "
                f"cleared {len(checkpoint_ids)} checkpoints"
            )
            
    except Exception as e:
        logger.error(f"Failed to cleanup stale story states: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    with Session(engine) as session:
        init_db(session)

    # Cleanup stale story states from previous run
    await cleanup_stale_story_states()
    
    # Start scheduler for periodic tasks (agent token reset, cleanup)
    from app.services.singletons import get_scheduler_service
    scheduler = get_scheduler_service()
    scheduler.start()

    from app.kafka import ensure_kafka_topics
    try:
        topics_ok = await ensure_kafka_topics()
        if not topics_ok:
            logger.warning("[SYSTEM] Some Kafka topics failed to create")
    except Exception as e:
        logger.warning(f"Failed to ensure Kafka topics: {e}")

    from app.agents.routers.router_service import start_router_service, stop_router_service
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
        import traceback
        logger.warning(f"⚠️ Failed to initialize agent pools: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")

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
        # Shutdown scheduler
        try:
            scheduler.shutdown()
        except (Exception, asyncio.CancelledError) as e:
            logger.error(f"Error stopping scheduler: {e}")
        
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

        from app.services.pool_registry_service import get_pool_registry
        try:
            registry = get_pool_registry()
            for pool_name, manager in list(registry.items()):
                try:
                    await manager.stop(graceful=True)
                except (Exception, asyncio.CancelledError) as e:
                    logger.error(f"Error stopping pool '{pool_name}': {e}")
            registry.clear()
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

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
