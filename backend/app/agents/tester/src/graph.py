"""Tester LangGraph with Setup → Plan → Implement → Review → Run flow.

Optimized flow (no summarize):
  router → setup_workspace → plan → implement → review → run_tests → END
      ↓                                   ↑        │           ↓
 test_status                              └─ LBTM ─┘     analyze_errors
 conversation
      ↓
     END

Updated with PostgresSaver for checkpoint/pause/resume support (aligned with Developer V2).
"""

import logging
from functools import partial
from typing import Literal, Optional, Any

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.tester.src.core_nodes import (
    conversation,
    router,
    send_response,
    test_status,
)
from app.agents.tester.src.nodes.analyze_errors import analyze_errors
from app.agents.tester.src.nodes.implement_tests import implement_tests
from app.agents.tester.src.nodes.plan_tests import plan_tests
from app.agents.tester.src.nodes.review import review
from app.agents.tester.src.nodes.run_tests import run_tests
from app.agents.tester.src.nodes.setup_workspace import setup_workspace
from app.agents.tester.src.state import TesterState

logger = logging.getLogger(__name__)


# =============================================================================
# PostgresSaver Singleton (aligned with Developer V2)
# =============================================================================

_postgres_checkpointer: Optional[AsyncPostgresSaver] = None
_connection_pool = None


async def get_postgres_checkpointer() -> AsyncPostgresSaver:
    """Get or create a PostgresSaver checkpointer for persistent state.
    
    Aligned with Developer V2 implementation for consistent checkpoint handling.
    """
    global _postgres_checkpointer, _connection_pool
    
    if _postgres_checkpointer is None:
        from app.core.config import settings
        from psycopg_pool import AsyncConnectionPool
        
        # Convert SQLAlchemy URI to standard PostgreSQL connection string
        db_uri = str(settings.SQLALCHEMY_DATABASE_URI)
        if "+psycopg" in db_uri:
            db_uri = db_uri.replace("+psycopg", "")
        
        # Create async connection pool (required for proper checkpoint saving)
        _connection_pool = AsyncConnectionPool(
            conninfo=db_uri,
            min_size=1,
            max_size=3,
            open=False,
            kwargs={"autocommit": True},
        )
        await _connection_pool.open(wait=True)
        
        _postgres_checkpointer = AsyncPostgresSaver(_connection_pool)
        # Create tables if they don't exist
        await _postgres_checkpointer.setup()
        logger.info("[TesterGraph] PostgresSaver initialized")
    
    return _postgres_checkpointer


# =============================================================================
# Interrupt Signal Check (aligned with Developer V2)
# =============================================================================

def check_interrupt_signal(story_id: str, agent=None) -> str | None:
    """Check for interrupt signal from agent's in-memory signal store.
    
    Signal is pushed by AgentPoolManager.signal_agent() when user clicks cancel/pause.
    
    Args:
        story_id: Story UUID string
        agent: Agent instance for signal check
        
    Returns:
        'pause', 'cancel', or None
    """
    if not story_id:
        return None
    
    if agent is not None and hasattr(agent, 'check_signal'):
        signal = agent.check_signal(story_id)
        if signal:
            import logging
            logging.getLogger(__name__).info(f"[Signal] {signal} found in agent for story {story_id[:8]}...")
            return signal
    return None


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================


def route_after_router(
    state: TesterState,
) -> Literal["setup_workspace", "test_status", "conversation"]:
    """Route based on action from router node."""
    action = state.get("action", "CONVERSATION")

    if action == "PLAN_TESTS":
        return "setup_workspace"  # Go through setup first
    elif action == "TEST_STATUS":
        return "test_status"
    return "conversation"


def route_after_implement(
    state: TesterState,
) -> Literal["review", "run_tests"]:
    """Route after implement: go to review or run_tests.
    
    With parallel execution, implement_tests handles ALL steps at once,
    so we always go to review (which also handles all files at once).
    """
    use_code_review = state.get("use_code_review", True)  # Default ON
    
    if use_code_review:
        return "review"
    
    # Skip review - go directly to run_tests
    return "run_tests"


def route_after_review(
    state: TesterState,
) -> Literal["implement_tests", "run_tests"]:
    """Route based on review result (LGTM/LBTM).
    
    With parallel execution:
    - LBTM: Re-implement only the FAILED files (stored in failed_files)
    - LGTM: All files passed -> run_tests
    
    Max 2 review cycles to prevent infinite loops.
    """
    review_result = state.get("review_result", "LGTM")
    review_count = state.get("review_count", 0)
    failed_files = state.get("failed_files", [])
    
    logger.info(f"[route_after_review] review_result={review_result}, review_count={review_count}, failed_files={len(failed_files)}")
    
    # LBTM with failed files: re-implement only failed files
    max_reviews = 2
    if review_result == "LBTM" and failed_files and review_count < max_reviews:
        logger.info(f"[route_after_review] LBTM -> re-implement {len(failed_files)} failed files")
        return "implement_tests"
    
    # LGTM or max reviews reached -> run_tests
    if review_count >= max_reviews and failed_files:
        logger.info(f"[route_after_review] Max reviews ({max_reviews}) reached - proceeding to run_tests")
    else:
        logger.info("[route_after_review] All files LGTM -> run_tests")
    
    return "run_tests"


def route_after_run(state: TesterState) -> Literal["analyze_errors", "send_response"]:
    """Route after run: analyze errors or send response."""
    run_status = state.get("run_status", "PASS")
    debug_count = state.get("debug_count", 0)
    max_debug = state.get("max_debug", 3)

    if run_status == "PASS":
        return "send_response"

    if debug_count < max_debug:
        return "analyze_errors"

    return "send_response"


def route_after_analyze(
    state: TesterState,
) -> Literal["implement_tests", "send_response"]:
    """Route after error analysis: retry implementation or give up."""
    error_analysis = state.get("error_analysis", "")
    test_plan = state.get("test_plan", [])

    if error_analysis and test_plan:
        return "implement_tests"
    return "send_response"


# ============================================================================
# GRAPH
# ============================================================================


class TesterGraph:
    """LangGraph-based Tester with optimized flow.

    Flow:
    router → setup_workspace → plan → implement → review → run_tests → END
        ↓                                  ↑         │           ↓
   test_status                             └─ LBTM ──┘     analyze_errors
   conversation
        ↓
       END

    Nodes (8 total):
    1. router - Entry point, decide action
    2. setup_workspace - Git worktree, project context
    3. plan_tests - Create test plan with pre-loaded dependencies
    4. implement_tests - Generate tests using structured output
    5. review - LGTM/LBTM code review
    6. run_tests - Execute tests
    7. analyze_errors - Debug failing tests
    8. send_response - Final message to user
    
    Supports checkpointing for pause/resume functionality (aligned with Developer V2).
    Uses PostgresSaver for persistent checkpoints across restarts.
    """

    def __init__(self, agent=None, checkpointer: Optional[Any] = None):
        self.agent = agent
        self.checkpointer = checkpointer  # Will be set async if None
        self._graph_compiled = False

        graph = StateGraph(TesterState)

        # ===== NODES =====
        # Router (entry point - also queries stories and gets tech_stack)
        graph.add_node("router", partial(router, agent=agent))
        
        # Setup workspace (git worktree, project context)
        graph.add_node("setup_workspace", partial(setup_workspace, agent=agent))

        # Main flow: Plan → Implement → Review → Run
        graph.add_node("plan_tests", partial(plan_tests, agent=agent))
        graph.add_node("implement_tests", partial(implement_tests, agent=agent))
        graph.add_node("review", partial(review, agent=agent))
        graph.add_node("run_tests", partial(run_tests, agent=agent))
        graph.add_node("analyze_errors", partial(analyze_errors, agent=agent))
        graph.add_node("send_response", partial(send_response, agent=agent))

        # Tool-based nodes
        graph.add_node("test_status", partial(test_status, agent=agent))
        graph.add_node("conversation", partial(conversation, agent=agent))

        # ===== EDGES =====
        # Entry point: router
        graph.set_entry_point("router")

        # Router conditional edges
        graph.add_conditional_edges(
            "router",
            route_after_router,
            {
                "setup_workspace": "setup_workspace",
                "test_status": "test_status",
                "conversation": "conversation",
            },
        )
        
        # Setup → Plan
        graph.add_edge("setup_workspace", "plan_tests")

        # Test generation flow: plan → implement
        graph.add_edge("plan_tests", "implement_tests")

        # After implement → review (parallel: all steps done at once)
        graph.add_conditional_edges(
            "implement_tests",
            route_after_implement,
            {
                "review": "review",
                "run_tests": "run_tests",
            },
        )

        # Review routing: LBTM → implement, LGTM → [implement or run_tests]
        graph.add_conditional_edges(
            "review",
            route_after_review,
            {
                "implement_tests": "implement_tests",
                "run_tests": "run_tests",
            },
        )

        # Run → Analyze or Respond
        graph.add_conditional_edges(
            "run_tests",
            route_after_run,
            {
                "analyze_errors": "analyze_errors",
                "send_response": "send_response",
            },
        )

        # Analyze → Implement or Respond
        graph.add_conditional_edges(
            "analyze_errors",
            route_after_analyze,
            {
                "implement_tests": "implement_tests",
                "send_response": "send_response",
            },
        )

        # End nodes
        graph.add_edge("send_response", END)
        graph.add_edge("test_status", END)
        graph.add_edge("conversation", END)

        self._state_graph = graph
        self.graph = None  # Will be compiled with checkpointer
        self.recursion_limit = 50  # Increased from default 25
    
    async def setup(self) -> None:
        """Setup the graph with PostgresSaver checkpointer (aligned with Developer V2)."""
        if self.graph is not None:
            return  # Already setup
        
        if self.checkpointer is None:
            try:
                self.checkpointer = await get_postgres_checkpointer()
                logger.info(f"[TesterGraph] PostgresSaver setup OK: {type(self.checkpointer).__name__}")
            except Exception as e:
                logger.warning(f"[TesterGraph] Failed to setup PostgresSaver, using MemorySaver: {e}", exc_info=True)
                self.checkpointer = MemorySaver()
        
        self.graph = self._state_graph.compile(checkpointer=self.checkpointer)
        logger.info(f"[TesterGraph] Graph compiled with checkpointer: {type(self.checkpointer).__name__}")
    
    def setup_sync(self) -> None:
        """Setup the graph with MemorySaver (sync fallback)."""
        if self.graph is not None:
            return
        self.checkpointer = self.checkpointer or MemorySaver()
        self.graph = self._state_graph.compile(checkpointer=self.checkpointer)
        logger.info("[TesterGraph] Graph compiled with MemorySaver (sync fallback)")
