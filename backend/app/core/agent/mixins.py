"""Agent mixins for reusable functionality.

Mixins provide common patterns that can be mixed into agent classes.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from uuid import UUID

from sqlmodel import Session
from app.core.db import engine
from app.models import Story
from app.models.base import StoryAgentState

logger = logging.getLogger(__name__)


class StoryStoppedException(Exception):
    """Raised when story processing should stop (pause/cancel)."""
    
    def __init__(self, story_id: str, state: StoryAgentState, message: str = ""):
        self.story_id = story_id
        self.state = state
        self.message = message or f"Story {story_id} stopped with state: {state.value}"
        super().__init__(self.message)


class PausableAgentMixin:
    """Mixin providing pause/resume/cancel functionality for agents.
    
    This mixin assumes the parent class has:
    - self.agent_id: UUID
    - self.check_signal(story_id: str) -> Optional[str]
    - self.clear_signal(story_id: str) -> None
    - self.consume_signal(story_id: str) -> Optional[str]
    - self.name: str (for logging)
    
    Usage:
        class MyAgent(BaseAgent, PausableAgentMixin):
            def __init__(self, ...):
                super().__init__(...)
                self.init_pausable_mixin()
    """
    
    def init_pausable_mixin(self):
        """Initialize mixin state. Call this in agent __init__."""
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._paused_stories: Set[str] = set()
        self._cancelled_stories: Set[str] = set()
        
        # NEW: In-memory checkpoint cache (fallback when PostgresSaver fails)
        self._checkpoint_cache: Dict[str, dict] = {}
        self._checkpoint_cache_max_size = 10  # LRU cache
    
    def get_story_state_from_db(self, story_id: str) -> Optional[StoryAgentState]:
        """Get current story agent_state from database (source of truth).
        
        Args:
            story_id: Story UUID string
            
        Returns:
            StoryAgentState or None if story not found
        """
        try:
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                return story.agent_state if story else None
        except Exception as e:
            logger.error(f"[{self.name}] Failed to get story state from DB: {e}")
            return None
    
    def check_should_stop(self, story_id: str) -> None:
        """Check if story should stop. Raises StoryStoppedException if cancelled/paused.
        
        Checks both:
        1. In-memory signal (set by API endpoint)
        2. Database state (source of truth)
        
        Args:
            story_id: Story UUID string
            
        Raises:
            StoryStoppedException: If story should be paused or cancelled
        """
        # Check in-memory signal first (faster)
        signal = self.check_signal(story_id)
        if signal == "cancel":
            self._cancelled_stories.add(story_id)
            raise StoryStoppedException(story_id, StoryAgentState.CANCEL_REQUESTED, "Cancel requested")
        elif signal == "pause":
            self._paused_stories.add(story_id)
            raise StoryStoppedException(story_id, StoryAgentState.PAUSED, "Paused")
        
        # Check database state (source of truth)
        state = self.get_story_state_from_db(story_id)
        if state in [StoryAgentState.CANCEL_REQUESTED, StoryAgentState.CANCELED]:
            self._cancelled_stories.add(story_id)
            raise StoryStoppedException(story_id, state, "Cancelled")
        elif state == StoryAgentState.PAUSED:
            self._paused_stories.add(story_id)
            raise StoryStoppedException(story_id, state, "Paused")
    
    def is_story_paused(self, story_id: str) -> bool:
        """Check if story is paused.
        
        Args:
            story_id: Story UUID string
            
        Returns:
            True if story is paused
        """
        if story_id in self._paused_stories:
            return True
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.PAUSED:
            self._paused_stories.add(story_id)
            return True
        return False
    
    def is_story_cancelled(self, story_id: str) -> bool:
        """Check if story is cancelled.
        
        Args:
            story_id: Story UUID string
            
        Returns:
            True if story is cancelled
        """
        if story_id in self._cancelled_stories:
            return True
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.CANCELED:
            self._cancelled_stories.add(story_id)
            return True
        return False
    
    async def pause_story(self, story_id: str) -> bool:
        """Pause a running story task.
        
        Args:
            story_id: Story UUID string
            
        Returns:
            True if task was paused, False if not running
        """
        logger.info(f"[{self.name}] Pausing story: {story_id}")
        self._paused_stories.add(story_id)
        
        task = self._running_tasks.get(story_id)
        if task and not task.done():
            task.cancel()
            return True
        
        return False
    
    async def cancel_story(self, story_id: str) -> bool:
        """Cancel a running story task.
        
        Args:
            story_id: Story UUID string
            
        Returns:
            True if task was cancelled, False if not running
        """
        logger.info(f"[{self.name}] Cancelling story: {story_id}")
        self._cancelled_stories.add(story_id)
        
        task = self._running_tasks.get(story_id)
        if task and not task.done():
            task.cancel()
            await self._cleanup_story(story_id)
            return True
        
        return False
    
    async def resume_story(self, story_id: str) -> bool:
        """Check if story can be resumed from checkpoint.
        
        Args:
            story_id: Story UUID string
            
        Returns:
            True if story can be resumed (has checkpoint_thread_id)
        """
        try:
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if not story:
                    logger.error(f"Story {story_id} not found")
                    return False
                
                # Check if has checkpoint (required for resume)
                if not story.checkpoint_thread_id:
                    logger.warning(f"Cannot resume: no checkpoint for {story_id}")
                    return False
                
                self._paused_stories.discard(story_id)
                logger.info(f"[{self.name}] Story {story_id} ready to resume from checkpoint: {story.checkpoint_thread_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to validate resume state: {e}")
            return False
    
    async def _cleanup_story(self, story_id: str):
        """Cleanup resources for a cancelled/finished story.
        
        Args:
            story_id: Story UUID string
        """
        try:
            # Remove from tracking
            self._running_tasks.pop(story_id, None)
            self._cancelled_stories.discard(story_id)
            self._paused_stories.discard(story_id)
            self.clear_signal(story_id)
            
            # Cleanup DB resources (agent-specific override can extend this)
            await self._cleanup_story_db_resources(story_id)
            
        except Exception as e:
            logger.error(f"[{self.name}] Cleanup error for story {story_id}: {e}")
    
    async def _cleanup_story_db_resources(self, story_id: str):
        """Cleanup story-specific DB resources (override in subclass if needed).
        
        Default implementation clears running_pid and running_port.
        
        Args:
            story_id: Story UUID string
        """
        try:
            import os
            import signal
            
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if story and story.running_pid:
                    try:
                        os.kill(story.running_pid, signal.SIGTERM)
                    except (ProcessLookupError, OSError):
                        pass
                    story.running_pid = None
                    story.running_port = None
                    session.commit()
        except Exception as e:
            logger.debug(f"[{self.name}] DB cleanup error: {e}")
    
    def clear_story_cache(self, story_id: str) -> None:
        """Clear story from caches for restart.
        
        Args:
            story_id: Story UUID string
        """
        self._cancelled_stories.discard(story_id)
        self._paused_stories.discard(story_id)
        self._running_tasks.pop(story_id, None)
        self.clear_signal(story_id)
    
    async def _update_story_state(self, story_id: str, state: StoryAgentState) -> bool:
        """Update story agent_state in database with WebSocket broadcast.
        
        Args:
            story_id: Story UUID string
            state: New agent state
            
        Returns:
            True if update successful
        """
        from app.websocket.connection_manager import connection_manager
        
        project_id = None
        old_state = None
        
        try:
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if not story:
                    logger.error(f"[{self.name}] Story {story_id} not found")
                    return False
                
                old_state = story.agent_state
                project_id = story.project_id
                story.agent_state = state
                story.assigned_agent_id = self.agent_id
                session.commit()
            
            logger.info(f"[{self.name}] Story {story_id} agent_state: {old_state} → {state} (assigned_agent_id={self.agent_id})")
            
            # Broadcast state change to frontend
            if project_id:
                try:
                    await connection_manager.broadcast_to_project({
                        "type": "story_state_changed",
                        "story_id": story_id,
                        "agent_state": state.value if state else None,
                        "old_state": old_state.value if old_state else None,
                    }, project_id)
                    logger.debug(f"[{self.name}] Broadcasted agent_state change: {state.value}")
                except Exception as broadcast_err:
                    logger.warning(f"[{self.name}] Failed to broadcast state change: {broadcast_err}")
            
            return True
        
        except Exception as e:
            logger.error(f"[{self.name}] Failed to update story state: {e}", exc_info=True)
            return False
    
    async def _run_graph_with_signal_check(self, graph, input_data, config, story_id: str):
        """Run graph with DB state checking (single source of truth) and checkpoint validation.
        
        FIX #1: Use DB as single source of truth to eliminate race conditions.
        FIX #2: Validate checkpoint periodically to detect serialization failures.
        
        Args:
            graph: LangGraph compiled graph
            input_data: Initial state or Command
            config: Graph config with thread_id
            story_id: Story UUID string
            
        Returns:
            Final state from graph execution
            
        Raises:
            StoryStoppedException: If story is paused or cancelled
        """
        final_state = None
        node_count = 0
        last_checkpoint_node = 0
        
        # FIX #1: Check DB state before start (authoritative source)
        db_state = self.get_story_state_from_db(story_id)
        if db_state in [StoryAgentState.CANCEL_REQUESTED, StoryAgentState.CANCELED]:
            raise StoryStoppedException(story_id, db_state, "Cancelled before start")
        elif db_state == StoryAgentState.PAUSED:
            raise StoryStoppedException(story_id, db_state, "Paused before start")
        
        async for event in graph.astream(input_data, config, stream_mode="values"):
            node_count += 1
            final_state = event
            
            # FIX #2: Validate checkpoint every 3 nodes to detect serialization failures
            if node_count - last_checkpoint_node >= 3:
                try:
                    checkpoint = await self.graph_engine.checkpointer.aget(config)
                    if checkpoint:
                        last_checkpoint_node = node_count
                        logger.debug(f"[{self.name}] Checkpoint verified at node {node_count}")
                    else:
                        logger.warning(f"[{self.name}] Checkpoint missing at node {node_count}")
                except Exception as e:
                    logger.error(f"[{self.name}] Checkpoint validation failed at node {node_count}: {e}")
                    # Continue execution - non-critical error
            
            # FIX #1: SINGLE CHECK from DB only (removed in-memory signal check)
            db_state = self.get_story_state_from_db(story_id)
            
            if db_state in [StoryAgentState.CANCEL_REQUESTED, StoryAgentState.CANCELED]:
                self._cancelled_stories.add(story_id)  # Update cache after DB check
                raise StoryStoppedException(story_id, db_state, "Cancelled (DB check)")
            elif db_state == StoryAgentState.PAUSED:
                self._paused_stories.add(story_id)  # Update cache after DB check
                # FIX #2: Verify checkpoint before pause
                try:
                    checkpoint = await self.graph_engine.checkpointer.aget(config)
                    if not checkpoint:
                        logger.error(f"[{self.name}] Cannot pause: no checkpoint available!")
                except Exception as e:
                    logger.error(f"[{self.name}] Checkpoint check failed on pause: {e}")
                raise StoryStoppedException(story_id, db_state, "Paused (DB check)")
        
        logger.info(f"[{self.name}] Graph completed after {node_count} nodes")
        return final_state
    
    async def _save_checkpoint_with_fallback(self, story_id: str, state: dict, config: dict) -> bool:
        """Save checkpoint with fallback to memory cache.
        
        FIX #2: Fallback mechanism for checkpoint serialization failures.
        
        Args:
            story_id: Story UUID string
            state: State dict to checkpoint
            config: Graph config with thread_id
            
        Returns:
            True if saved to DB, False if fell back to memory
        """
        try:
            # Try PostgresSaver first
            await self.graph_engine.checkpointer.aput(config, state)
            logger.debug(f"[{self.name}] Checkpoint saved to DB for {story_id}")
            return True
        except Exception as e:
            logger.warning(f"[{self.name}] DB checkpoint failed, using memory cache: {e}")
            
            # Fallback: save to memory (LRU)
            self._checkpoint_cache[story_id] = {
                "state": state,
                "config": config,
                "timestamp": datetime.now().isoformat()
            }
            
            # Evict oldest if cache full
            if len(self._checkpoint_cache) > self._checkpoint_cache_max_size:
                oldest_key = min(self._checkpoint_cache.keys(), 
                               key=lambda k: self._checkpoint_cache[k]["timestamp"])
                del self._checkpoint_cache[oldest_key]
                logger.debug(f"[{self.name}] Evicted checkpoint for {oldest_key}")
            
            return False  # Indicate fallback was used
    
    async def _load_checkpoint_with_fallback(self, story_id: str, config: dict) -> Optional[dict]:
        """Load checkpoint with fallback to memory cache.
        
        FIX #2: Fallback mechanism for checkpoint loading.
        
        Args:
            story_id: Story UUID string
            config: Graph config with thread_id
            
        Returns:
            Checkpoint state dict or None if not found
        """
        try:
            # Try PostgresSaver first
            checkpoint = await self.graph_engine.checkpointer.aget(config)
            if checkpoint:
                logger.debug(f"[{self.name}] Checkpoint loaded from DB for {story_id}")
                return checkpoint
        except Exception as e:
            logger.warning(f"[{self.name}] DB checkpoint load failed: {e}")
        
        # Fallback: load from memory cache
        cached = self._checkpoint_cache.get(story_id)
        if cached:
            logger.info(f"[{self.name}] Checkpoint loaded from memory cache for {story_id}")
            return cached["state"]
        
        return None
