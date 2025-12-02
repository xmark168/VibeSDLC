"""Tester LangGraph with Plan → Implement → Run flow (Simplified)."""

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
from app.agents.tester.src.nodes.run_tests import run_tests
from app.agents.tester.src.state import TesterState

logger = logging.getLogger(__name__)


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================


def route_after_router(
    state: TesterState,
) -> Literal["plan_tests", "test_status", "conversation"]:
    """Route based on action from router node."""
    action = state.get("action", "CONVERSATION")

    if action == "PLAN_TESTS":
        return "plan_tests"
    elif action == "TEST_STATUS":
        return "test_status"
    return "conversation"


def route_after_implement(
    state: TesterState,
) -> Literal["implement_tests", "run_tests"]:
    """Route after implement: continue implementing or run tests."""
    current = state.get("current_step", 0)
    total = state.get("total_steps", 0)

    if current < total:
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
    """LangGraph-based Tester with simplified Plan → Implement → Run flow.

     Flow:
     router → plan_tests → implement_tests ⟷ run_tests → END
         ↓          ↑              ↓
    test_status  analyze_errors ←─┘
    conversation
         ↓
        END
    """

    def __init__(self, agent=None):
        self.agent = agent

        graph = StateGraph(TesterState)

        # ===== NODES =====
        # Router (entry point - also queries stories and gets tech_stack)
        graph.add_node("router", partial(router, agent=agent))

        # Main flow: Plan → Implement → Run
        graph.add_node("plan_tests", partial(plan_tests, agent=agent))
        graph.add_node("implement_tests", partial(implement_tests, agent=agent))
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
                "plan_tests": "plan_tests",
                "test_status": "test_status",
                "conversation": "conversation",
            },
        )

        # Test generation flow: plan → implement
        graph.add_edge("plan_tests", "implement_tests")

        # Implement loop
        graph.add_conditional_edges(
            "implement_tests",
            route_after_implement,
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

        self.graph = graph.compile()
        logger.info("[TesterGraph] Compiled with Plan → Implement → Run flow")
