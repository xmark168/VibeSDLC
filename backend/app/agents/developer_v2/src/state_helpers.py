"""State helper functions for type-safe state access.

Provides pack/unpack functions to convert between flat LangGraph state
and typed Pydantic models.

Usage:
    from app.agents.developer_v2.src.state_helpers import unpack_story, unpack_workspace

    async def my_node(state: DeveloperState) -> DeveloperState:
        story = unpack_story(state)
        ws = unpack_workspace(state)
        
        # Use typed access
        print(story.title, ws.path)
"""

from typing import Dict, Any

from app.agents.developer_v2.src.schemas import (
    StoryInput,
    WorkspaceState,
    PlanState,
    ReviewState,
    DebugState,
    SummarizeState,
    RunCodeState,
)


# =============================================================================
# Unpack functions (state dict -> Pydantic model)
# =============================================================================

def unpack_story(state: Dict[str, Any]) -> StoryInput:
    """Extract story input from state."""
    return StoryInput(
        story_id=state.get("story_id", ""),
        epic=state.get("epic", ""),
        title=state.get("story_title", ""),
        description=state.get("story_description", ""),
        requirements=state.get("story_requirements", []),
        acceptance_criteria=state.get("acceptance_criteria", []),
        project_id=state.get("project_id", ""),
        task_id=state.get("task_id", ""),
        user_id=state.get("user_id", ""),
    )


def unpack_workspace(state: Dict[str, Any]) -> WorkspaceState:
    """Extract workspace state from state."""
    return WorkspaceState(
        path=state.get("workspace_path", ""),
        branch=state.get("branch_name", ""),
        main=state.get("main_workspace", ""),
        ready=state.get("workspace_ready", False),
        index_ready=state.get("index_ready", False),
    )


def unpack_plan(state: Dict[str, Any]) -> PlanState:
    """Extract plan state from state."""
    return PlanState(
        steps=state.get("implementation_plan", []),
        logic_analysis=state.get("logic_analysis", []),
        current_step=state.get("current_step", 0),
        total_steps=state.get("total_steps", 0),
        dependencies_content=state.get("dependencies_content", {}),
    )


def unpack_review(state: Dict[str, Any]) -> ReviewState:
    """Extract review state from state."""
    return ReviewState(
        result=state.get("review_result"),
        feedback=state.get("review_feedback"),
        details=state.get("review_details"),
        count=state.get("review_count", 0),
        total_lbtm=state.get("total_lbtm_count", 0),
    )


def unpack_debug(state: Dict[str, Any]) -> DebugState:
    """Extract debug state from state."""
    return DebugState(
        count=state.get("debug_count", 0),
        max_attempts=state.get("max_debug", 5),
        history=state.get("debug_history", []),
        error_analysis=state.get("error_analysis"),
    )


def unpack_summarize(state: Dict[str, Any]) -> SummarizeState:
    """Extract summarize state from state."""
    return SummarizeState(
        summary=state.get("summary"),
        todos=state.get("todos", {}),
        is_pass=state.get("is_pass"),
        feedback=state.get("summarize_feedback"),
        count=state.get("summarize_count", 0),
    )


def unpack_run_code(state: Dict[str, Any]) -> RunCodeState:
    """Extract run code state from state."""
    return RunCodeState(
        status=state.get("run_status"),
        result=state.get("run_result"),
        stdout=state.get("run_stdout", ""),
        stderr=state.get("run_stderr", ""),
    )


# =============================================================================
# Pack functions (Pydantic model -> state dict updates)
# =============================================================================

def pack_story(model: StoryInput) -> Dict[str, Any]:
    """Convert story input to state dict fields."""
    return {
        "story_id": model.story_id,
        "epic": model.epic,
        "story_title": model.title,
        "story_description": model.description,
        "story_requirements": model.requirements,
        "acceptance_criteria": model.acceptance_criteria,
        "project_id": model.project_id,
        "task_id": model.task_id,
        "user_id": model.user_id,
    }


def pack_workspace(model: WorkspaceState) -> Dict[str, Any]:
    """Convert workspace state to state dict fields."""
    return {
        "workspace_path": model.path,
        "branch_name": model.branch,
        "main_workspace": model.main,
        "workspace_ready": model.ready,
        "index_ready": model.index_ready,
    }


def pack_plan(model: PlanState) -> Dict[str, Any]:
    """Convert plan state to state dict fields."""
    return {
        "implementation_plan": model.steps,
        "logic_analysis": model.logic_analysis,
        "current_step": model.current_step,
        "total_steps": model.total_steps,
        "dependencies_content": model.dependencies_content,
    }


def pack_review(model: ReviewState) -> Dict[str, Any]:
    """Convert review state to state dict fields."""
    return {
        "review_result": model.result,
        "review_feedback": model.feedback,
        "review_details": model.details,
        "review_count": model.count,
        "total_lbtm_count": model.total_lbtm,
    }


def pack_debug(model: DebugState) -> Dict[str, Any]:
    """Convert debug state to state dict fields."""
    return {
        "debug_count": model.count,
        "max_debug": model.max_attempts,
        "debug_history": model.history,
        "error_analysis": model.error_analysis,
    }


def pack_summarize(model: SummarizeState) -> Dict[str, Any]:
    """Convert summarize state to state dict fields."""
    return {
        "summary": model.summary,
        "todos": model.todos,
        "is_pass": model.is_pass,
        "summarize_feedback": model.feedback,
        "summarize_count": model.count,
    }


def pack_run_code(model: RunCodeState) -> Dict[str, Any]:
    """Convert run code state to state dict fields."""
    return {
        "run_status": model.status,
        "run_result": model.result,
        "run_stdout": model.stdout,
        "run_stderr": model.stderr,
    }
