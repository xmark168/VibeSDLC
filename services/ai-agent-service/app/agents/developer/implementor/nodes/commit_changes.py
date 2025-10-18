"""
Commit Changes Node

Commit tất cả changes với meaningful commit message sử dụng Git tools.
"""

import json

from langchain_core.messages import AIMessage

from ..state import GitOperation, ImplementorState
from ..tool.git_tools_gitpython import commit_changes_tool
from ..utils.validators import validate_git_operations


def commit_changes(state: ImplementorState) -> ImplementorState:
    """
    Commit tất cả changes với meaningful commit message.

    Args:
        state: ImplementorState với implemented changes

    Returns:
        Updated ImplementorState với commit info
    """
    try:
        print("💾 Committing changes...")

        # Determine working directory
        working_dir = state.codebase_path or "."

        # Generate meaningful commit message
        commit_message = _generate_commit_message(state)

        # Validate commit message
        git_valid, git_issues = validate_git_operations(
            branch_name=state.feature_branch,
            commit_message=commit_message,
            base_branch=state.base_branch,
        )
        if not git_valid:
            print(f"⚠️  Commit validation issues: {'; '.join(git_issues)}")

        # Get list of files to commit
        files_to_commit = []
        files_to_commit.extend(state.files_created)
        files_to_commit.extend(state.files_modified)

        # Remove duplicates
        files_to_commit = list(set(files_to_commit))

        print(f"  📝 Commit message: {commit_message}")
        print(f"  📄 Files to commit: {len(files_to_commit)}")

        # Commit changes using Git tools
        result = commit_changes_tool(
            message=commit_message,
            files=files_to_commit if files_to_commit else None,  # None = commit all
            working_directory=working_dir,
        )

        # Parse result
        result_data = json.loads(result)

        if result_data.get("status") == "success":
            commit_hash = result_data.get("commit_hash", "")
            commit_short_hash = result_data.get("commit_short_hash", "")
            files_committed = result_data.get("files_committed", [])

            # Record Git operation
            git_op = GitOperation(
                operation="commit",
                commit_hash=commit_hash,
                commit_message=commit_message,
                files_changed=files_committed,
                status="success",
            )
            state.git_operations.append(git_op)

            # Update state
            state.final_commit_hash = commit_hash

            # Store result in tools output
            state.tools_output["commit"] = result_data

            # Update status
            state.current_phase = "create_pr"
            state.status = "changes_committed"

            # Add message
            message = AIMessage(
                content=f"✅ Changes committed successfully\n"
                f"- Commit: {commit_short_hash}\n"
                f"- Message: {commit_message}\n"
                f"- Files: {len(files_committed)}\n"
                f"- Next: Create Pull Request"
            )
            state.messages.append(message)

            print(f"✅ Changes committed - {commit_short_hash}")

        else:
            # Handle error
            error_msg = result_data.get("message", "Unknown error committing changes")
            state.error_message = f"Commit failed: {error_msg}"
            state.status = "error"

            # Add error message
            message = AIMessage(content=f"❌ Failed to commit changes: {error_msg}")
            state.messages.append(message)

            print(f"❌ Commit failed: {error_msg}")

        return state

    except Exception as e:
        state.error_message = f"Commit failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ Commit error: {str(e)}")
        state.messages.append(message)

        print(f"❌ Commit failed: {e}")
        return state


def _generate_commit_message(state: ImplementorState) -> str:
    """
    Generate meaningful commit message based on implementation.

    Args:
        state: ImplementorState với implementation details

    Returns:
        Commit message string
    """
    # Start with task description
    if state.task_description:
        # Clean up task description for commit message
        task_desc = state.task_description.strip()
        if len(task_desc) > 50:
            task_desc = task_desc[:47] + "..."

        commit_msg = f"feat: {task_desc}"
    else:
        commit_msg = "feat: implement new functionality"

    # Add details about changes
    details = []

    if state.files_created:
        details.append(f"- Add {len(state.files_created)} new files")

    if state.files_modified:
        details.append(f"- Modify {len(state.files_modified)} existing files")

    # Add tech stack info for new projects
    if state.is_new_project and state.tech_stack:
        details.append(f"- Initialize {state.tech_stack} project")

    # Add test status if tests were run
    if hasattr(state.test_execution, "passed"):
        if state.test_execution.passed:
            details.append("- All tests passing")
        else:
            details.append("- Tests need attention")

    # Combine message
    if details:
        commit_msg += "\n\n" + "\n".join(details)

    return commit_msg
