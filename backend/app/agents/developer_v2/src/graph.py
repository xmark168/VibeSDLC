"""Developer V2 LangGraph Definition."""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    router, setup_workspace, analyze, design, plan, implement, clarify, respond,
    merge_to_main, cleanup_workspace, code_review, run_code, debug_error, summarize_code
)


def route(state: DeveloperState) -> Literal["setup_workspace", "clarify", "respond"]:
    """Route to appropriate node based on action.
    
    If action requires code modification (ANALYZE/DESIGN/PLAN/IMPLEMENT) -> setup_workspace first
    If action is CLARIFY or RESPOND -> go directly (no workspace needed)
    """
    action = state.get("action")
    
    # Actions that need workspace (will modify code)
    if action in ["ANALYZE", "DESIGN", "PLAN", "IMPLEMENT"]:
        return "setup_workspace"
    if action == "CLARIFY":
        return "clarify"
    return "respond"


def route_after_workspace(state: DeveloperState) -> Literal["analyze", "design", "plan", "implement"]:
    """Route to actual work node after workspace is setup.
    
    Flow: analyze -> design -> plan -> implement
    """
    action = state.get("action")
    
    if action == "ANALYZE":
        return "analyze"
    if action == "DESIGN":
        return "design"
    if action == "PLAN":
        return "plan"
    return "implement"


def route_after_analyze(state: DeveloperState) -> Literal["design", "plan"]:
    """Route after analyze - skip design for low complexity tasks.
    
    Speed optimization: Low complexity tasks don't need full system design.
    """
    complexity = state.get("complexity", "medium")
    
    # Skip design for low complexity tasks (saves 1 LLM call)
    if complexity == "low":
        return "plan"
    
    return "design"


def should_continue(state: DeveloperState) -> Literal["implement", "summarize_code", "respond"]:
    """Check if implementation should continue or move to summarize (MetaGPT pattern)."""
    action = state.get("action")
    error = state.get("error")
    
    # If error occurred, go to respond
    if error:
        return "respond"
    
    # If action is RESPOND (from failed node), go to respond
    if action == "RESPOND":
        return "respond"
    
    # If action is PLAN (from implement with empty plan), go to respond with error
    # This handles the case where plan extraction failed
    if action == "PLAN":
        return "respond"
    
    # If action is VALIDATE (all steps completed), go to summarize_code (MetaGPT pattern)
    if action == "VALIDATE":
        return "summarize_code"
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    # Check if there are steps to implement
    if total_steps == 0:
        return "respond"  # No steps = nothing to do
    
    if action == "IMPLEMENT" and current_step < total_steps:
        return "implement"
    
    # All steps completed, go to summarize_code (MetaGPT SummarizeCode pattern)
    return "summarize_code"


def route_after_summarize(state: DeveloperState) -> Literal["code_review", "run_code", "implement", "respond"]:
    """Route after summarize_code completes (MetaGPT IS_PASS pattern).
    
    - If IS_PASS=True -> code_review (or skip for simple tasks)
    - If IS_PASS=False and under max_summarize -> implement (loop back with feedback)
    - Otherwise -> code_review (proceed anyway after max attempts)
    
    Speed optimization: Skip code_review for simple tasks (low complexity, < 3 files)
    """
    action = state.get("action")
    is_pass = state.get("is_pass", True)
    summarize_count = state.get("summarize_count", 0)
    max_summarize = state.get("max_summarize", 3)
    
    # If action explicitly set
    if action == "CODE_REVIEW":
        return "code_review"
    if action == "IMPLEMENT":
        return "implement"
    if action == "RESPOND":
        return "respond"
    
    # IS_PASS check
    if is_pass:
        # Speed optimization: Skip code_review for simple tasks
        complexity = state.get("complexity", "medium")
        files_created = state.get("files_created", [])
        files_modified = state.get("files_modified", [])
        total_files = len(files_created) + len(files_modified)
        
        if complexity == "low" and total_files <= 3:
            return "run_code"  # Skip code_review, go directly to run tests
        
        return "code_review"
    
    # Not pass - can we retry?
    if summarize_count < max_summarize:
        return "implement"  # Loop back with feedback
    
    # Max attempts reached, proceed to code review anyway
    return "code_review"


def route_after_code_review(state: DeveloperState) -> Literal["run_code", "implement", "respond"]:
    """Route after code review completes.
    
    - If passed (LGTM) -> run_code
    - If not passed (LBTM) and can retry -> implement (fix code based on review feedback)
    - Otherwise -> run_code (proceed anyway after max iterations)
    """
    code_review_passed = state.get("code_review_passed", True)
    iteration = state.get("code_review_iteration", 0)
    k = state.get("code_review_k", 2)
    
    if code_review_passed:
        return "run_code"
    
    # LBTM: Go back to implement to fix the code based on review feedback
    if iteration < k:
        return "implement"
    
    return "run_code"  # Proceed even if not all passed after max iterations


def route_after_run_code(state: DeveloperState) -> Literal["merge_to_main", "debug_error", "respond", "implement"]:
    """Route after running tests (MetaGPT React Loop pattern).
    
    - If tests passed -> merge_to_main
    - If failed and can debug -> debug_error
    - If react_mode and under max_react_loop -> implement (retry full cycle)
    - Otherwise -> respond with failure
    """
    run_result = state.get("run_result", {})
    status = run_result.get("status", "PASS")
    debug_count = state.get("debug_count", 0)
    max_debug = state.get("max_debug", 5)  # MetaGPT pattern
    
    # React loop mode (MetaGPT Engineer2 pattern)
    react_mode = state.get("react_mode", False)
    react_loop_count = state.get("react_loop_count", 0)
    max_react_loop = state.get("max_react_loop", 40)  # MetaGPT Engineer2 pattern
    
    # HARD LIMIT: Circuit breaker to prevent infinite loops
    total_attempts = debug_count + react_loop_count
    if total_attempts >= 50:  # Absolute maximum attempts (MetaGPT pattern)
        return "respond"
    
    if status == "PASS":
        return "merge_to_main"
    
    # Try debug first
    if debug_count < max_debug:
        return "debug_error"
    
    # React mode: retry full implementation cycle
    if react_mode and react_loop_count < max_react_loop:
        return "implement"
    
    return "respond"


class DeveloperGraph:
    """LangGraph-based Developer V2 for story processing.
    
    Flow:
    1. router - Decides if we need to modify code or just respond
    2. setup_workspace - Creates git branch + CocoIndex + loads AGENTS.md
    3. analyze - Analyze story requirements
    4. design - System design with mermaid diagrams (MetaGPT Architect)
    5. plan - Create implementation plan
    6. implement - Code implementation
    7. summarize_code - MetaGPT SummarizeCode + IS_PASS check (loop back if not pass)
    8. code_review - LGTM/LBTM review with k iterations
    9. run_code - Execute tests to verify
    10. debug_error - Fix bugs if tests fail (up to max_debug attempts)
    11. merge_to_main - Merge branch after tests pass
    12. cleanup_workspace - Remove worktree and delete branch
    13. respond/clarify - Direct response
    
    Flow Diagram (MetaGPT-inspired):
    router → setup_workspace → analyze → design → plan → implement
                                                            ↓
                                                     summarize_code (IS_PASS check)
                                                      ↓ (PASS)    ↑ (NOT PASS)
                                                      code_review ─┘
                                                      ↓ (LGTM)   ↑ (LBTM)
                                                      run_code ──┘
                                                      ↓ (PASS)   ↓ (FAIL)
                                                 merge_to_main  debug_error
                                                      ↓              ↓
                                               cleanup_workspace  run_code
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
        g.add_node("summarize_code", partial(summarize_code, agent=agent))  # MetaGPT SummarizeCode + IS_PASS
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
        # Speed optimization: skip design for low complexity tasks
        g.add_conditional_edges("analyze", route_after_analyze)
        g.add_edge("design", "plan")
        g.add_edge("plan", "implement")
        
        # After implement: continue or go to summarize_code (MetaGPT pattern)
        g.add_conditional_edges("implement", should_continue)
        
        # After summarize_code: IS_PASS check - loop back to implement or proceed to code_review
        g.add_conditional_edges("summarize_code", route_after_summarize)
        
        # After code review: run tests or retry review
        g.add_conditional_edges("code_review", route_after_code_review)
        
        # After run code: merge if pass, debug if fail
        g.add_conditional_edges("run_code", route_after_run_code)
        
        # Debug error loops back to run_code
        g.add_edge("debug_error", "run_code")
        
        # Merge and cleanup flow
        g.add_edge("merge_to_main", "cleanup_workspace")
        g.add_edge("cleanup_workspace", "respond")
        
        # End nodes
        g.add_edge("clarify", END)
        g.add_edge("respond", END)
        
        self.graph = g.compile()
