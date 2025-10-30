"""
Create PR Node

Tạo Pull Request sử dụng Git tools.
"""

import json

from langchain_core.messages import AIMessage

from ..state import GitOperation, ImplementorState
from ..tool.git_tools_gitpython import create_pull_request_tool


def create_pr(state: ImplementorState) -> ImplementorState:
    """
    Tạo Pull Request cho implementation.

    Args:
        state: ImplementorState với committed changes

    Returns:
        Updated ImplementorState với PR info
    """
    try:
        print("🔀 Creating Pull Request...")

        # Determine working directory
        working_dir = state.codebase_path or "."

        # Generate PR title and description
        pr_title, pr_description = _generate_pr_content(state)

        print(f"  📋 PR Title: {pr_title}")

        # Create PR using Git tools
        result = create_pull_request_tool.invoke(
            {
                "title": pr_title,
                "description": pr_description,
                "base_branch": state.base_branch,
                "working_directory": working_dir,
                "draft": False,
            }
        )

        # Parse result
        result_data = json.loads(result)

        if result_data.get("status") == "branch_pushed":
            # Git tools push branch but don't create actual PR (needs GitHub/GitLab API)
            # This is expected behavior

            source_branch = result_data.get("source_branch", state.feature_branch)
            target_branch = result_data.get("target_branch", state.base_branch)
            remote_url = result_data.get("remote_url", "")

            # Record Git operation
            git_op = GitOperation(
                operation="create_pr",
                branch_name=source_branch,
                pr_title=pr_title,
                pr_description=pr_description,
                status="branch_pushed",
            )
            state.git_operations.append(git_op)

            # Store result in tools output
            state.tools_output["pr_creation"] = result_data

            # Update status
            state.current_phase = "finalize"
            state.status = "pr_ready"

            # Add message with next steps
            message = AIMessage(
                content=f"✅ Branch pushed for Pull Request\n"
                f"- Title: {pr_title}\n"
                f"- Branch: {source_branch} → {target_branch}\n"
                f"- Remote: {remote_url}\n"
                f"- Next: Visit Git platform to create PR\n"
                f"- Status: Ready for finalization"
            )
            state.messages.append(message)

            print("✅ Branch pushed - ready for PR creation on Git platform")

        else:
            # Handle error
            error_msg = result_data.get("message", "Unknown error creating PR")
            state.error_message = f"PR creation failed: {error_msg}"
            state.status = "error"

            # Add error message
            message = AIMessage(content=f"❌ Failed to create PR: {error_msg}")
            state.messages.append(message)

            print(f"❌ PR creation failed: {error_msg}")

        return state

    except Exception as e:
        state.error_message = f"PR creation failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ PR creation error: {str(e)}")
        state.messages.append(message)

        print(f"❌ PR creation failed: {e}")
        return state


def _generate_pr_content(state: ImplementorState) -> tuple[str, str]:
    """
    Generate PR title and description based on implementation.

    Args:
        state: ImplementorState với implementation details

    Returns:
        Tuple of (title, description)
    """
    # Generate title
    if state.task_description:
        title = state.task_description.strip()
        if len(title) > 72:  # GitHub PR title limit
            title = title[:69] + "..."
    else:
        title = "Implement new functionality"

    # Generate description
    description_parts = []

    # Add task description
    if state.task_description:
        description_parts.append(f"## Description\n{state.task_description}")

    # Add implementation summary
    summary_parts = []
    if state.files_created:
        summary_parts.append(f"- **{len(state.files_created)} new files** created")
    if state.files_modified:
        summary_parts.append(
            f"- **{len(state.files_modified)} existing files** modified"
        )
    if state.is_new_project:
        summary_parts.append(f"- **New {state.tech_stack} project** initialized")

    if summary_parts:
        description_parts.append("## Changes\n" + "\n".join(summary_parts))

    # Add file details
    if state.files_created or state.files_modified:
        file_details = []

        if state.files_created:
            file_details.append("### New Files")
            for file_path in state.files_created[:10]:  # Limit to first 10
                file_details.append(f"- `{file_path}`")
            if len(state.files_created) > 10:
                file_details.append(f"- ... and {len(state.files_created) - 10} more")

        if state.files_modified:
            file_details.append("### Modified Files")
            for file_path in state.files_modified[:10]:  # Limit to first 10
                file_details.append(f"- `{file_path}`")
            if len(state.files_modified) > 10:
                file_details.append(f"- ... and {len(state.files_modified) - 10} more")

        description_parts.append("\n".join(file_details))

    # Add test status
    if hasattr(state.test_execution, "passed"):
        if state.test_execution.passed:
            description_parts.append("## Testing\n✅ All tests passing")
        else:
            description_parts.append("## Testing\n⚠️ Some tests need attention")

    # Add implementation notes
    notes = []
    if state.is_new_project:
        notes.append("- This is a new project initialization")
    if state.boilerplate_template:
        notes.append(f"- Used boilerplate template: `{state.boilerplate_template}`")

    if notes:
        description_parts.append("## Notes\n" + "\n".join(notes))

    description = "\n\n".join(description_parts)

    return title, description
