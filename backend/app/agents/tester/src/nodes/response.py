"""Response node - Final output and cleanup."""

import logging
from uuid import UUID

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.nodes.helpers import send_message
from app.models.base import StoryAgentState
from app.agents.developer.src.utils.story_logger import StoryLogger

logger = logging.getLogger(__name__)


async def send_response(state: TesterState, agent=None) -> dict:
    """Send final response after test generation flow."""
    stories = state.get("stories", [])
    
    if stories and not state.get("story_id"):
        state["story_id"] = stories[0].get("id")
    
    story_logger = StoryLogger.from_state(state, agent).with_node("send_response")
    error = state.get("error")
    test_plan = state.get("test_plan", [])
    run_status = state.get("run_status", "")
    run_result = state.get("run_result", {})
    files_created = state.get("files_created", [])
    workspace_path = state.get("workspace_path", "")
    branch_name = state.get("branch_name", "")
    workspace_ready = state.get("workspace_ready", False)

    commit_msg = ""
    
    # Commit on PASS, revert on FAIL/ERROR
    if workspace_ready and workspace_path:
        from app.utils.workspace_utils import commit_workspace_changes
        from app.agents.tester.src.tools.workspace_tools import revert_test_changes
        
        if run_status == "PASS" and files_created:
            try:
                story_titles = ", ".join(s.get("title", "")[:30] for s in stories[:2]) if stories else "tests"
                commit_result = commit_workspace_changes(
                    workspace_path=workspace_path,
                    title=story_titles,
                    branch_name=branch_name or "test",
                    agent_name="tester",
                )
                if commit_result.get("success"):
                    commit_msg = f"\n\n📝 {commit_result.get('message', 'Changes committed')}"
                    await story_logger.info(f"Committed: {commit_result.get('message')}")
            except Exception as e:
                await story_logger.warning(f"Failed to commit: {e}")
        elif run_status in ["FAIL", "ERROR"]:
            try:
                revert_test_changes(workspace_path)
                await story_logger.info(f"Reverted changes due to {run_status}")
            except Exception as e:
                await story_logger.warning(f"Failed to revert: {e}")

    # Build message
    if error:
        msg = f"❌ Có lỗi xảy ra: {error}"
    elif run_status == "PASS":
        passed = run_result.get("passed", 0)
        msg = f"✅ Tests passed! ({passed} tests passed)"
        if files_created:
            msg += f"\n\nFiles created:\n" + "\n".join(f"  - {f}" for f in files_created)
        msg += commit_msg
    elif run_status == "ERROR":
        setup_error = run_result.get("setup_error") or run_result.get("error") or "Unknown setup error"
        msg = f"⚠️ Setup Error: {setup_error}\n\nTests could not run."
    elif run_status == "FAIL":
        passed = run_result.get("passed", 0)
        failed = run_result.get("failed", 0)
        msg = f"❌ Tests failed! ({passed} passed, {failed} failed)"
    elif not test_plan:
        msg = "Không có tests được tạo."
    else:
        msg = f"✅ Đã tạo test plan với {len(test_plan)} steps."
        if files_created:
            msg += f"\n\nFiles created:\n" + "\n".join(f"  - {f}" for f in files_created)
        msg += commit_msg

    # Update story states
    if agent and stories:
        for story in stories:
            story_id = story["id"]
            try:
                await agent._update_story_state(story_id, StoryAgentState.FINISHED)
                await story_logger.info(f"Updated story {story_id[:8]} to FINISHED")
            except Exception as e:
                await story_logger.error(f"Failed to update story {story_id[:8]}: {e}")

    await send_message(state, agent, msg, "test_result")

    return {"message": msg, "merged": bool(commit_msg)}
