"""Developer V2 LangGraph Definition."""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    router, setup_workspace, analyze, design, plan, implement, validate, clarify, respond,
    merge_to_main, cleanup_workspace, code_review, run_code, debug_error
)


def route(state: DeveloperState) -> Literal["setup_workspace", "clarify", "respond"]:
    """Route to appropriate node based on action.
    
    If action requires code modification (ANALYZE/PLAN/IMPLEMENT/VALIDATE) -> setup_workspace first
    If action is CLARIFY or RESPOND -> go directly (no workspace needed)
    """
    action = state.get("action")
    
    # Actions that need workspace (will modify code)
    if action in ["ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE"]:
        return "setup_workspace"
    if action == "CLARIFY":
        return "clarify"
    return "respond"


def route_after_workspace(state: DeveloperState) -> Literal["analyze", "plan", "implement", "validate"]:
    """Route to actual work node after workspace is setup."""
    action = state.get("action")
    
    if action == "ANALYZE":
        return "analyze"
    if action == "PLAN":
        return "plan"
    if action == "IMPLEMENT":
        return "implement"
    return "validate"


def should_continue(state: DeveloperState) -> Literal["implement", "code_review", "respond"]:
    """Check if implementation should continue or move to code review."""
    action = state.get("action")
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if action == "IMPLEMENT" and current_step < total_steps:
        return "implement"
    
    # All steps completed, go to code review
    return "code_review"


def route_after_code_review(state: DeveloperState) -> Literal["run_code", "code_review", "respond"]:
    """Route after code review completes.
    
    - If passed (LGTM) -> run_code
    - If not passed and can retry -> code_review again
    - Otherwise -> respond
    """
    code_review_passed = state.get("code_review_passed", True)
    iteration = state.get("code_review_iteration", 0)
    k = state.get("code_review_k", 2)
    
    if code_review_passed:
        return "run_code"
    
    if iteration < k:
        return "code_review"
    
    return "run_code"  # Proceed even if not all passed after max iterations


def route_after_run_code(state: DeveloperState) -> Literal["merge_to_main", "debug_error", "respond"]:
    """Route after running tests.
    
    - If tests passed -> merge_to_main
    - If failed and can debug -> debug_error
    - Otherwise -> respond with failure
    """
    run_result = state.get("run_result", {})
    status = run_result.get("status", "PASS")
    debug_count = state.get("debug_count", 0)
    max_debug = state.get("max_debug", 3)
    
    if status == "PASS":
        return "merge_to_main"
    
    if debug_count < max_debug:
        return "debug_error"
    
    return "respond"


def route_after_validate(state: DeveloperState) -> Literal["code_review", "implement", "respond"]:
    """Route after validation completes.
    
    - If validation passed (is_pass=True) -> code_review
    - If needs revision and under max attempts -> implement (retry)
    - Otherwise -> respond (report failure)
    """
    is_pass = state.get("is_pass", False)
    needs_revision = state.get("needs_revision", False)
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 3)
    
    if is_pass:
        return "code_review"
    
    if needs_revision and revision_count < max_revisions:
        return "implement"
    
    return "respond"


class DeveloperGraph:
    """LangGraph-based Developer V2 for story processing.
    
    Flow:
    1. router - Decides if we need to modify code or just respond
    2. setup_workspace - Creates git branch + CocoIndex
    3. analyze/plan/implement - Code implementation
    4. code_review - LGTM/LBTM review with k iterations
    5. run_code - Execute tests to verify
    6. debug_error - Fix bugs if tests fail (up to max_debug attempts)
    7. merge_to_main - Merge branch after tests pass
    8. cleanup_workspace - Remove worktree and delete branch
    9. respond/clarify - Direct response
    
    Flow Diagram:
    router → setup_workspace → analyze → plan → implement
                                                    ↓
                                              code_review
                                              ↓ (LGTM)   ↑ (LBTM, retry)
                                              run_code ──┘
                                              ↓ (PASS)   ↓ (FAIL)
                                         merge_to_main  debug_error
                                              ↓              ↓
                                       cleanup_workspace  run_code (retry)
                                              ↓
                                           respond → END
    """
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        # Add all nodes
        g.add_node("router", partial(router, agent=agent))
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("analyze", partial(analyze, agent=agent))
        g.add_node("design", partial(design, agent=agent))  # MetaGPT Architect pattern
        g.add_node("plan", partial(plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("validate", partial(validate, agent=agent))
        g.add_node("code_review", partial(code_review, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("debug_error", partial(debug_error, agent=agent))
        g.add_node("merge_to_main", partial(merge_to_main, agent=agent))
        g.add_node("cleanup_workspace", partial(cleanup_workspace, agent=agent))
        g.add_node("clarify", partial(clarify, agent=agent))
        g.add_node("respond", partial(respond, agent=agent))
        
        # Entry point
        g.set_entry_point("router")
        
        # Router decides: need workspace or direct response
        g.add_conditional_edges("router", route)
        
        # After workspace setup, route to actual work
        g.add_conditional_edges("setup_workspace", route_after_workspace)
        
        # Work flow edges (MetaGPT pattern: analyze → design → plan → implement)
        g.add_edge("analyze", "design")
        g.add_edge("design", "plan")
        g.add_edge("plan", "implement")
        
        # After implement: continue or go to code review
        g.add_conditional_edges("implement", should_continue)
        
        # After code review: run tests or retry review
        g.add_conditional_edges("code_review", route_after_code_review)
        
        # After run code: merge if pass, debug if fail
        g.add_conditional_edges("run_code", route_after_run_code)
        
        # Debug error loops back to run_code
        g.add_edge("debug_error", "run_code")
        
        # After validate: code review if pass, retry if needed (legacy path)
        g.add_conditional_edges("validate", route_after_validate)
        
        # Merge and cleanup flow
        g.add_edge("merge_to_main", "cleanup_workspace")
        g.add_edge("cleanup_workspace", "respond")
        
        # End nodes
        g.add_edge("clarify", END)
        g.add_edge("respond", END)
        
        self.graph = g.compile()
