"""
Developer V2 LangGraph Definition.
"""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    router, setup_workspace, analyze, design, plan, implement, clarify, respond,
    merge_to_main, cleanup_workspace, code_review, run_code, debug_error, summarize_code,
    lint_and_format
)


def route(state: DeveloperState) -> Literal["setup_workspace", "clarify"]:
    """
    Entry point routing: determine if workspace setup is needed.
    """
    action = state.get("action")
    
    if action == "CLARIFY":
        return "clarify"
    # All other actions go through setup_workspace -> implementation flow
    return "setup_workspace"


def route_after_workspace(state: DeveloperState) -> Literal["analyze", "design", "plan", "implement"]:
    """
    Route to actual work node after workspace setup completes.
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
    """
    Route after analysis: skip design for simple tasks (optimization).
    """
    complexity = state.get("complexity", "medium")
    if complexity == "low":
        return "plan"
    
    return "design"


def should_continue(state: DeveloperState) -> Literal["implement", "summarize_code", "cleanup_workspace"]:
    """Implementation loop control: continue steps or move to quality gate.
    
    Routes:
    - More steps remaining -> implement (continue loop)
    - All steps done (VALIDATE) -> summarize_code (MetaGPT quality gate)
    - Error occurred -> cleanup_workspace (abort)
    - No steps defined -> cleanup_workspace (nothing to do)
    """
    action = state.get("action")
    error = state.get("error")
    
    # If error occurred, cleanup and end
    if error:
        return "cleanup_workspace"
    
    # If action is VALIDATE (all steps completed), go to summarize_code (MetaGPT pattern)
    if action == "VALIDATE":
        return "summarize_code"
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    # Check if there are steps to implement
    if total_steps == 0:
        return "cleanup_workspace"  # No steps = nothing to do
    
    if action == "IMPLEMENT" and current_step < total_steps:
        return "implement"
    
    # All steps completed, go to summarize_code (MetaGPT SummarizeCode pattern)
    return "summarize_code"


def route_after_summarize(state: DeveloperState) -> Literal["lint_and_format", "run_code", "implement"]:
    """First quality gate: IS_PASS check (MetaGPT SummarizeCode pattern).
    
    LLM evaluates if implementation meets requirements. Routes:
    - IS_PASS=True -> lint_and_format -> code_review (or run_code for simple tasks)
    - IS_PASS=False + retries available -> implement (retry with feedback)
    - Max attempts reached -> lint_and_format (proceed anyway)
    
    Optimization: Skip lint_and_format + code_review for low complexity + ≤3 files.
    Max retries: 3 iterations (configurable via max_summarize).
    """
    action = state.get("action")
    is_pass = state.get("is_pass", True)
    summarize_count = state.get("summarize_count", 0)
    max_summarize = state.get("max_summarize", 3)
    
    # If action explicitly set
    if action == "CODE_REVIEW":
        return "lint_and_format"
    if action == "IMPLEMENT":
        return "implement"
    
    # IS_PASS check
    if is_pass:
        # Speed optimization: Skip lint + code_review for simple tasks
        complexity = state.get("complexity", "medium")
        files_created = state.get("files_created", [])
        files_modified = state.get("files_modified", [])
        total_files = len(files_created) + len(files_modified)
        
        if complexity == "low" and total_files <= 3:
            return "run_code"  # Skip lint + code_review, go directly to run tests
        
        return "lint_and_format"
    
    # Not pass - can we retry?
    if summarize_count < max_summarize:
        return "implement"  # Loop back with feedback
    
    # Max attempts reached, proceed to lint + code review anyway
    return "lint_and_format"


def route_after_code_review(state: DeveloperState) -> Literal["run_code", "implement"]:
    """Second quality gate: code review (LGTM/LBTM pattern).
    
    LLM reviews all code changes in batch. Routes:
    - LGTM (Looks Good To Me) -> run_code (proceed to tests)
    - LBTM (Looks Bad To Me) + retries available -> implement (fix issues)
    - Max iterations reached -> run_code (proceed anyway)
    
    Default iterations: k=1 (one review pass) for speed.
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


def route_after_run_code(state: DeveloperState) -> Literal["merge_to_main", "debug_error", "cleanup_workspace", "implement"]:
    """Third quality gate: test execution with self-healing (MetaGPT React pattern).
    
    Runs auto-detected tests (npm/pnpm/pytest). Routes:
    - Tests PASS -> merge_to_main (success path)
    - Tests FAIL + debug retries available -> debug_error (fix & retry)
    - Debug exhausted + React mode -> implement (full cycle retry with feedback)
    - All retries exhausted -> cleanup_workspace (abort)
    
    Safety limits:
    - max_debug: 5 attempts (quick fixes)
    - max_react_loop: 40 iterations (MetaGPT Engineer2 pattern)
    - Hard limit: 50 total attempts (circuit breaker)
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
        return "cleanup_workspace"
    
    if status == "PASS":
        return "merge_to_main"
    
    # Try debug first
    if debug_count < max_debug:
        return "debug_error"
    
    # React mode: retry full implementation cycle
    if react_mode and react_loop_count < max_react_loop:
        return "implement"
    
    return "cleanup_workspace"


class DeveloperGraph:
    """LangGraph-based Developer V2 workflow for automated story implementation.
    
    Complete SDLC workflow with MetaGPT-inspired patterns:
    
    1. router - Entry routing (workspace needed or direct response)
    2. setup_workspace - Git worktree + CocoIndex + project context
    3. analyze - Requirements analysis (task type, complexity, affected files)
    4. design - System architecture with mermaid (MetaGPT Architect, skipped for low complexity)
    5. plan - Implementation plan (ordered steps with file paths)
    6. implement - Code generation with ReAct tools (read, search, write)
    7. summarize_code - Quality gate #1: IS_PASS check (MetaGPT SummarizeCode)
    8. code_review - Quality gate #2: LGTM/LBTM batch review
    9. run_code - Quality gate #3: Auto-detected test execution
    10. debug_error - Self-healing bug fixes with LLM analysis
    11. merge_to_main - Git merge to main branch (success path)
    12. cleanup_workspace - Remove worktree & branch (cleanup)
    13. respond - Final response to user
    14. clarify - Ask questions when requirements unclear
    
    Key Features:
    - Workspace isolation: Each story gets a separate git worktree
    - Semantic search: CocoIndex for relevant code context (8-15 files)
    - Project awareness: Loads AGENTS.md, detects framework (Next.js/React/Python)
    - Quality gates: 3-stage validation (IS_PASS, code review, tests)
    - Self-healing: Debug loop (5 attempts) + React mode (40 full cycles)
    - Optimization: Skip design for low complexity, skip review for simple tasks
    
    Tools Used:
    - workspace_tools: setup_git_worktree, commit_workspace_changes
    - CocoIndex: get_related_code_indexed, search_codebase, incremental_update_index
    - Execution: detect_test_command, execute_command_async, install_dependencies
    - Context: get_agents_md, get_project_context, detect_project_structure, get_boilerplate_examples
    
    Utils:
    - llm_utils: execute_llm_with_tools (ReAct pattern), get_langfuse_config
    - prompt_utils: format_input_template, build_system_prompt, get_prompt
    
    Flow Diagram:
                     ┌─────────┐
                     │ router  │ (entry)
                     └────┬────┘
                          │
                ┌─────────┴──────────┐
                │                    │
         ┌──────▼──────┐      ┌─────▼─────┐
         │setup_workspace│      │  clarify  │ → END
         └──────┬──────┘      └───────────┘
                │
         ┌──────▼──────┐
         │   analyze   │
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │   design    │ (skip if low complexity)
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │    plan     │
         └──────┬──────┘
                │
         ┌──────▼──────┐
    ┌───│  implement  │◄───────┐
    │   └──────┬──────┘        │
    │          │                │
    │   ┌──────▼───────┐       │
    │   │summarize_code│       │ (IS_PASS retry)
    │   └──────┬───────┘       │
    │          │ (PASS)         │
    │   ┌──────▼──────┐        │
    │   │code_review  │        │ (LBTM retry)
    │   └──────┬──────┘        │
    │          │ (LGTM)         │
    │   ┌──────▼──────┐        │
    │   │  run_code   │◄───┐   │
    │   └──────┬──────┘    │   │
    │          │ (FAIL)     │   │
    │   ┌──────▼──────┐    │   │
    │   │debug_error  │────┘   │ (debug retry)
    │   └─────────────┘        │
    │                           │
    └───────────────────────────┘ (React full retry)
                │ (PASS)
         ┌──────▼──────┐
         │merge_to_main│
         └──────┬──────┘
                │
      ┌─────────▼─────────┐
      │cleanup_workspace  │
      └─────────┬─────────┘
                │
         ┌──────▼──────┐
         │   respond   │ → END
         └─────────────┘
    
    MetaGPT Patterns:
    - Architect: System design with mermaid diagrams before coding
    - SummarizeCode: IS_PASS quality gate with retry feedback
    - Engineer2: React mode for full cycle retries (max 40 iterations)
    - RunCode: Auto test execution with dependency installation
    
    State Management:
    - State: DeveloperState (TypedDict) passed between nodes
    - Persistence: Each node returns updated state dict
    - Routing: Conditional edges based on state values (action, complexity, results)
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
        g.add_node("lint_and_format", partial(lint_and_format, agent=agent))  # Auto-fix style before review
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
        
        # After summarize_code: IS_PASS check - loop back to implement or proceed to lint_and_format
        g.add_conditional_edges("summarize_code", route_after_summarize)
        
        # After lint_and_format: always go to code_review
        g.add_edge("lint_and_format", "code_review")
        
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
