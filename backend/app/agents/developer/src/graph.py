"""Developer V2 LangGraph - Story Implementation Workflow."""

from functools import partial
from typing import Literal, Optional, Any
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.developer.src.state import DeveloperState
from app.agents.developer.src.nodes import (
    setup_workspace, plan, implement, implement_parallel,
    run_code, analyze_error, review, respond,
)


def route_by_task_type(state: DeveloperState) -> Literal["respond", "setup_workspace"]:
    """Route based on graph_task_type"""
    task_type = state.get("graph_task_type", "implement_story")
    if task_type == "message":
        return "respond"
    return "setup_workspace"

def route_after_implement(state: DeveloperState) -> Literal["review", "implement", "run_code"]:
    """Route after implement. Skip review for low complexity."""
    complexity = state.get("complexity", "medium")
    if complexity == "low":
        current_step = state.get("current_step", 0)
        total_steps = state.get("total_steps", 0)
        return "implement" if current_step < total_steps else "run_code"
    
    if state.get("use_code_review", True):
        return "review"
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    return "implement" if current_step < total_steps else "run_code"


def route_review_result(state: DeveloperState) -> Literal["implement", "run_code"]:
    """Route based on review result (LGTM/LBTM)."""
    if state.get("review_result", "LGTM") == "LBTM":
        return "implement"
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    return "implement" if current_step < total_steps else "run_code"


def route_after_test(state: DeveloperState) -> Literal["analyze_error", "__end__"]:
    run_result = state.get("run_result", {})
    if run_result.get("status", "PASS") == "PASS":
        return "__end__"
    return "analyze_error" if state.get("debug_count", 0) < 5 else "__end__"


def route_after_setup(state: DeveloperState) -> Literal["plan", "__end__"]:
    """Route after setup - stop if setup failed."""
    if state.get("error") or not state.get("workspace_ready"):
        import logging
        logging.getLogger(__name__).error(
            f"[graph] Setup failed, stopping graph. Error: {state.get('error', 'workspace not ready')}"
        )
        return "__end__"
    return "plan"


def route_after_parallel(state: DeveloperState) -> Literal["run_code", "implement", "pause_checkpoint"]:
    """Route after parallel implement - fallback to sequential if errors."""
    
    if state.get("action") == "PAUSED":
        return "pause_checkpoint"
    
    parallel_errors = state.get("parallel_errors")
    
    # If parallel had errors, fallback to sequential implement
    if parallel_errors and len(parallel_errors) > 0:
        # Check if we haven't already tried sequential fallback
        if not state.get("_tried_sequential_fallback"):
            import logging
            logging.getLogger(__name__).warning(
                f"[graph] Parallel implement had {len(parallel_errors)} errors, falling back to sequential"
            )
            return "implement"
    
    return "run_code"


def route_after_analyze_error(state: DeveloperState) -> Literal["implement", "run_code", "__end__"]:
    """Route after analyze_error - handle IMPLEMENT, VALIDATE, or end."""
    action = state.get("action")
    if action == "IMPLEMENT":
        return "implement"
    elif action == "VALIDATE":
        return "run_code"  # Re-run build/test after auto-fix
    return "__end__"


async def pause_checkpoint(state: DeveloperState, agent=None) -> DeveloperState:
    """Checkpoint node for pause - calls interrupt() and resumes to implement_parallel."""
    from langgraph.types import interrupt
    interrupt({"reason": "pause", "node": "pause_checkpoint", "current_layer": state.get("current_layer", 0)})
    # After resume, clear PAUSED action to continue
    return {**state, "action": "IMPLEMENT"}


_postgres_checkpointer: Optional[AsyncPostgresSaver] = None
_connection_pool = None


async def get_postgres_checkpointer() -> AsyncPostgresSaver:
    """Get or create a PostgresSaver checkpointer for persistent state.
    
    Includes:
    - Health check for stale pools
    - Retry logic with exponential backoff
    - Timeouts to prevent indefinite hangs
    - Larger pool size for concurrent agents
    """
    import asyncio
    import logging
    global _postgres_checkpointer, _connection_pool
    
    logger = logging.getLogger(__name__)
    
    # Health check: Reset if pool is closed/stale
    if _connection_pool is not None:
        try:
            if _connection_pool.closed:
                logger.warning("[DeveloperGraph] Connection pool is closed, reinitializing...")
                _postgres_checkpointer = None
                _connection_pool = None
        except Exception:
            pass
    
    if _postgres_checkpointer is None:
        from app.core.config import settings
        from psycopg_pool import AsyncConnectionPool
        
        # Convert SQLAlchemy URI to standard PostgreSQL connection string
        db_uri = str(settings.SQLALCHEMY_DATABASE_URI)
        if "+psycopg" in db_uri:
            db_uri = db_uri.replace("+psycopg", "")
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"[DeveloperGraph] Creating connection pool (attempt {attempt + 1}/{max_retries})...")
                
                # Create async connection pool with larger size and connection timeout
                _connection_pool = AsyncConnectionPool(
                    conninfo=db_uri,
                    min_size=2,  # Increased from 1
                    max_size=10,  # Increased from 3 for concurrent agents
                    open=False,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,  # 5 seconds per connection attempt
                    },
                )
                
                # Open with timeout to prevent indefinite hang
                await asyncio.wait_for(
                    _connection_pool.open(wait=True),
                    timeout=10.0  # 10 seconds max for pool open
                )
                logger.info("[DeveloperGraph] Connection pool opened successfully")
                
                _postgres_checkpointer = AsyncPostgresSaver(_connection_pool)
                # Create tables if they don't exist
                await _postgres_checkpointer.setup()
                logger.info("[DeveloperGraph] PostgresSaver initialized successfully")
                break  # Success!
                
            except asyncio.TimeoutError:
                logger.warning(f"[DeveloperGraph] Connection pool open timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt  # Exponential: 1s, 2s, 4s
                    logger.info(f"[DeveloperGraph] Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    raise Exception("Failed to connect to PostgreSQL after 3 retries (timeout)")
                    
            except Exception as e:
                logger.error(f"[DeveloperGraph] PostgresSaver setup failed: {e}")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    logger.info(f"[DeveloperGraph] Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    raise
    
    return _postgres_checkpointer


class DeveloperGraph:
    """LangGraph for Developer V2 agent story implementation."""
    
    def __init__(self, agent=None, parallel=True, checkpointer: Optional[Any] = None):
        self.agent = agent
        self.parallel = parallel
        self.checkpointer = checkpointer  
        self._graph_compiled = False
        g = StateGraph(DeveloperState)
        # Entrypoint
        g.set_conditional_entry_point(route_by_task_type)
        # Chat node
        g.add_node("respond", partial(respond, agent=agent))
        
        # Story implementation nodes
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("plan", partial(plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("implement_parallel", partial(implement_parallel, agent=agent))
        g.add_node("pause_checkpoint", partial(pause_checkpoint, agent=agent))
        g.add_node("review", partial(review, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        
        # Chat nodes go directly to END
        g.add_edge("respond", "__end__")
        
        # Story implementation flow
        g.add_conditional_edges("setup_workspace", route_after_setup)
        
        if parallel:
            g.add_edge("plan", "implement_parallel")
            # Parallel → run_code, but fallback to sequential if errors, or pause_checkpoint
            g.add_conditional_edges("implement_parallel", route_after_parallel)
            g.add_edge("pause_checkpoint", "implement_parallel")  # Resume from pause
            g.add_edge("implement", "run_code")  # Sequential fallback path
        else:
            g.add_edge("plan", "implement")
            g.add_conditional_edges("implement", route_after_implement)
            g.add_conditional_edges("review", route_review_result)
        
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        
        self._state_graph = g
        self.graph = None  # Will be compiled with checkpointer
    
    async def setup(self) -> None:
        """Setup the graph with PostgresSaver checkpointer.
        
        Includes timeout and graceful fallback to MemorySaver if PostgreSQL unavailable.
        Total timeout: 30 seconds (3 retries × 10s each)
        """
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        
        if self.graph is not None:
            return  # Already setup
        
        if self.checkpointer is None:
            try:
                # Add timeout for entire setup (includes retries)
                self.checkpointer = await asyncio.wait_for(
                    get_postgres_checkpointer(),
                    timeout=30.0  # 30 seconds total (3 retries × 10s pool open)
                )
                logger.info(f"PostgresSaver setup OK: {type(self.checkpointer).__name__}")
            except asyncio.TimeoutError:
                logger.warning("PostgresSaver setup timeout after 30s, using MemorySaver")
                self.checkpointer = MemorySaver()
            except Exception as e:
                logger.warning(f"Failed to setup PostgresSaver, using MemorySaver: {e}", exc_info=True)
                self.checkpointer = MemorySaver()
        
        self.graph = self._state_graph.compile(checkpointer=self.checkpointer)
        logger.info(f"Graph compiled with checkpointer: {type(self.checkpointer).__name__}")
    
    def setup_sync(self) -> None:
        """Setup the graph with MemorySaver (sync fallback)."""
        if self.graph is not None:
            return
        self.checkpointer = self.checkpointer or MemorySaver()
        self.graph = self._state_graph.compile(checkpointer=self.checkpointer)
