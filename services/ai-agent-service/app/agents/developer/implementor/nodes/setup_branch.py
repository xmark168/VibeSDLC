"""
Setup Branch Node

Tạo feature branch cho implementation sử dụng Git tools.
"""

import json

from langchain_core.messages import AIMessage

from ..state import GitOperation, ImplementorState
from ..tool.git_tools_gitpython import create_feature_branch_tool


def setup_branch(state: ImplementorState) -> ImplementorState:
    """
    Tạo feature branch cho implementation.

    Args:
        state: ImplementorState với feature branch name

    Returns:
        Updated ImplementorState với branch setup info
    """
    try:
        print(f"🌿 Setting up feature branch: {state.feature_branch}")

        # Validate Git operations
        git_valid, git_issues = validate_git_operations(
            branch_name=state.feature_branch, base_branch=state.base_branch
        )
        if not git_valid:
            state.error_message = f"Invalid Git parameters: {'; '.join(git_issues)}"
            state.status = "error"
            return state

        # Determine working directory
        working_dir = state.codebase_path or "."

        # Create feature branch using Git tools
        result = create_feature_branch_tool(
            branch_name=state.feature_branch,
            base_branch=state.base_branch,
            working_directory=working_dir,
        )

        # Parse result
        result_data = json.loads(result)

        if result_data.get("status") == "success":
            state.current_branch = state.feature_branch

            # Record Git operation
            git_op = GitOperation(
                operation="create_branch",
                branch_name=state.feature_branch,
                status="success",
            )
            state.git_operations.append(git_op)

            # Store result in tools output
            state.tools_output["branch_creation"] = result_data

            # Update status
            if state.is_new_project and state.boilerplate_template:
                state.current_phase = "copy_boilerplate"
            else:
                state.current_phase = "implement_files"
            state.status = "branch_created"

            # Add message
            message = AIMessage(
                content=f"✅ Feature branch created successfully\n"
                f"- Branch: {state.feature_branch}\n"
                f"- Base: {state.base_branch}\n"
                f"- Next: {'Copy boilerplate' if state.is_new_project else 'Implement files'}"
            )
            state.messages.append(message)

            print(f"✅ Feature branch '{state.feature_branch}' created successfully")

        else:
            # Handle error
            error_msg = result_data.get("message", "Unknown error creating branch")
            state.error_message = f"Branch creation failed: {error_msg}"
            state.status = "error"

            # Add error message
            message = AIMessage(
                content=f"❌ Failed to create feature branch: {error_msg}"
            )
            state.messages.append(message)

            print(f"❌ Branch creation failed: {error_msg}")

        return state

    except Exception as e:
        state.error_message = f"Branch setup failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ Branch setup error: {str(e)}")
        state.messages.append(message)

        print(f"❌ Branch setup failed: {e}")
        return state
