"""Tester LangGraph with Setup → Plan → Implement → Review → Summarize → Run flow.

MetaGPT-style flow (aligned with Developer V2):
  router → setup_workspace → plan_tests → implement_tests → review → summarize → run_tests → END
      ↓                                          ↑           │                       ↓
 test_status                                     └── LBTM ───┘                 analyze_errors
 conversation
      ↓
     END
"""

import logging
from functools import partial
from typing import Literal

from langgraph.graph import END, StateGraph

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
from app.agents.tester.src.nodes.summarize import summarize
from app.agents.tester.src.nodes.run_tests import run_tests
from app.agents.tester.src.nodes.setup_workspace import setup_workspace
from app.agents.tester.src.state import TesterState

logger = logging.getLogger(__name__)


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
) -> Literal["review", "implement_tests", "summarize"]:
    """Route after implement: go to review (MetaGPT-style)."""
    use_code_review = state.get("use_code_review", True)  # Default ON
    
    if use_code_review:
        return "review"
    
    # Skip review - go to next step or summarize
    current = state.get("current_step", 0)
    total = state.get("total_steps", 0)
    
    if current < total:
        return "implement_tests"
    return "summarize"


def route_after_review(
    state: TesterState,
) -> Literal["implement_tests", "summarize", "run_tests"]:
    """Route based on review result (MetaGPT-style LGTM/LBTM).
    
    Note: Per-step LBTM limit (max 4) is enforced in review node.
    If step gets LBTM 4+ times, review node forces LGTM and increments current_step.
    
    Returns:
        - "implement_tests": LBTM, need to re-implement
        - "implement_tests": LGTM but more steps remain
        - "run_tests": All LGTM, skip summarize (optimization)
        - "summarize": Had LBTM, need final summary
    """
    review_result = state.get("review_result", "LGTM")
    review_count = state.get("review_count", 0)
    
    logger.info(f"[route_after_review] review_result={review_result}, review_count={review_count}")
    
    # LBTM: re-implement only if under max reviews limit
    max_reviews = 2
    if review_result == "LBTM" and review_count < max_reviews:
        logger.info(f"[route_after_review] LBTM -> re-implement (attempt {review_count + 1})")
        return "implement_tests"
    
    # If LBTM but max reviews reached, treat as LGTM (force advance)
    if review_result == "LBTM" and review_count >= max_reviews:
        logger.info(f"[route_after_review] LBTM but max reviews ({max_reviews}) reached -> advancing")
    
    # LGTM - check if more steps
    current = state.get("current_step", 0)
    total = state.get("total_steps", 0)
    
    if current < total:
        logger.info(f"[route_after_review] Advancing to next step ({current + 1}/{total})")
        return "implement_tests"
    
    # All steps done - skip summarize if all LGTM
    total_lbtm = state.get("total_lbtm_count", 0)
    if total_lbtm == 0:
        logger.info("[route_after_review] All LGTM -> run_tests")
        return "run_tests"
    
    logger.info("[route_after_review] Had LBTM -> summarize")
    return "summarize"


def route_after_summarize(
    state: TesterState,
) -> Literal["implement_tests", "run_tests"]:
    """Route based on IS_PASS result (MetaGPT-style).
    
    Returns:
        - "implement_tests": IS_PASS=NO, need to fix issues
        - "run_tests": IS_PASS=YES, proceed to run tests
    """
    is_pass = state.get("is_pass", "YES")
    summarize_count = state.get("summarize_count", 0)
    max_retries = 2
    
    if is_pass == "NO" and summarize_count < max_retries:
        return "implement_tests"
    
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
    """LangGraph-based Tester with MetaGPT-style flow (aligned with Developer V2).

    Flow:
    router → setup_workspace → plan_tests → implement_tests → review → summarize → run_tests → END
        ↓                                          ↑           │                       ↓
   test_status                                     └── LBTM ───┘                 analyze_errors
   conversation
        ↓
       END

    Nodes (9 total):
    1. router - Entry point, decide action
    2. setup_workspace - Git worktree, project context
    3. plan_tests - Create test plan with pre-loaded dependencies
    4. implement_tests - Generate tests using skills
    5. review - LGTM/LBTM code review (MetaGPT-style)
    6. summarize - IS_PASS final check (MetaGPT-style)
    7. run_tests - Execute tests
    8. analyze_errors - Debug failing tests
    9. send_response - Final message to user
    """

    def __init__(self, agent=None):
        self.agent = agent

        graph = StateGraph(TesterState)

        # ===== NODES =====
        # Router (entry point - also queries stories and gets tech_stack)
        graph.add_node("router", partial(router, agent=agent))
        
        # Setup workspace (git worktree, project context)
        graph.add_node("setup_workspace", partial(setup_workspace, agent=agent))

        # Main flow: Plan → Implement → Review → Summarize → Run
        graph.add_node("plan_tests", partial(plan_tests, agent=agent))
        graph.add_node("implement_tests", partial(implement_tests, agent=agent))
        graph.add_node("review", partial(review, agent=agent))
        graph.add_node("summarize", partial(summarize, agent=agent))
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

        # After implement → review (MetaGPT-style)
        graph.add_conditional_edges(
            "implement_tests",
            route_after_implement,
            {
                "review": "review",
                "implement_tests": "implement_tests",
                "summarize": "summarize",
            },
        )

        # Review routing: LBTM → implement, LGTM → [implement or summarize or run_tests]
        graph.add_conditional_edges(
            "review",
            route_after_review,
            {
                "implement_tests": "implement_tests",
                "summarize": "summarize",
                "run_tests": "run_tests",
            },
        )

        # Summarize routing: IS_PASS=NO → implement, YES → run_tests
        graph.add_conditional_edges(
            "summarize",
            route_after_summarize,
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

        # Compile with higher recursion limit for complex test generation
        self.graph = graph.compile()
        self.recursion_limit = 50  # Increased from default 25
        logger.info("[TesterGraph] Compiled with MetaGPT-style flow (Review + Summarize), recursion_limit=50")
