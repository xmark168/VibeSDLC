import logging
from typing import Optional, Any
from uuid import UUID

from sqlmodel import Session
from app.core.db import engine
from app.models import Story

logger = logging.getLogger(__name__)


def get_or_create_thread_id(
    story_id: str,
    agent_id: UUID,
    is_resume: bool = False
) -> str:
    try:
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if not story:
                raise ValueError(f"Story {story_id} not found")
            
            if is_resume:
                if not story.checkpoint_thread_id:
                    raise ValueError(f"Cannot resume: no checkpoint_thread_id for story {story_id}")
                thread_id = story.checkpoint_thread_id
                logger.info(f"[graph_helpers] Loaded checkpoint_thread_id from DB: {thread_id}")
            else:
                thread_id = f"{agent_id}_{story_id}"
                story.checkpoint_thread_id = thread_id
                session.commit()
                logger.info(f"[graph_helpers] Saved checkpoint_thread_id: {thread_id}")
            
            return thread_id
            
    except Exception as e:
        logger.error(f"[graph_helpers] Failed to get/create thread_id: {e}")
        raise


def langfuse_trace_context(
    trace_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    input_data: Optional[dict] = None,
    tags: Optional[list] = None,
    metadata: Optional[dict] = None
):
    langfuse_handler = None
    langfuse_ctx = None
    langfuse_span = None
    
    try:
        from app.core.config import settings
        if not settings.LANGFUSE_ENABLED:
            return None
        
        from langfuse import get_client
        
        langfuse = get_client()
        
        langfuse_ctx = langfuse.start_as_current_observation(
            as_type="span",
            name=trace_name
        )
        
        langfuse_span = langfuse_ctx.__enter__()
        
        langfuse_span.update_trace(
            user_id=user_id,
            session_id=session_id,
            input=input_data or {},
            tags=tags or [],
            metadata=metadata or {}
        )
        
        return langfuse_span
        
    except Exception as e:
        logger.debug(f"[graph_helpers] Langfuse setup error: {e}")
        return None
        
    finally:
        if langfuse_ctx:
            try:
                langfuse_ctx.__exit__(None, None, None)
            except Exception as e:
                logger.debug(f"[graph_helpers] Langfuse span close error: {e}")


def update_langfuse_trace_output(
    langfuse_ctx: Any,
    output_data: dict
) -> None:
    if not langfuse_ctx:
        return
    
    try:
        langfuse_span = langfuse_ctx.__enter__()
        langfuse_span.update_trace(output=output_data)
    except Exception as e:
        logger.debug(f"[graph_helpers] Failed to update trace output: {e}")
