"""
Setup Branch Node

Tạo feature branch cho implementation sử dụng Git tools.
"""

import json

from langchain_core.messages import AIMessage

from ..state import GitOperation, ImplementorState
from ..tool.git_tools_gitpython import create_feature_branch_tool
from ..utils.validators import validate_git_operations


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

        # Check if we're in test mode (skip branch creation if requested)
        test_mode = getattr(state, "test_mode", False)
        if test_mode:
            print("🧪 Test mode: Skipping branch creation")
            state.current_branch = state.feature_branch
            state.current_phase = "generate_code"
            state.status = "branch_ready"

            message = AIMessage(
                content=f"🧪 Test mode: Branch setup skipped\n"
                f"- Branch: {state.feature_branch}\n"
                f"- Next: Generate code"
            )
            state.messages.append(message)
            return state

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

        # Determine source branch for sequential branching
        source_branch = getattr(state, "source_branch", None)

        # Create feature branch using Git tools
        branch_params = {
            "branch_name": state.feature_branch,
            "base_branch": state.base_branch,
            "working_directory": working_dir,
        }

        # Add source_branch for sequential branching if specified
        if source_branch:
            branch_params["source_branch"] = source_branch
            print(f"🔗 Sequential branching: Creating from '{source_branch}'")

        result = create_feature_branch_tool.invoke(branch_params)

        # Parse result with error handling
        try:
            if not result or result.strip() == "":
                state.error_message = "Empty response from branch creation tool"
                state.status = "error"
                return state

            result_data = json.loads(result)
        except json.JSONDecodeError as e:
            state.error_message = f"Invalid JSON response from branch creation: {e}"
            state.status = "error"
            return state

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
            state.current_phase = "install_dependencies"
            state.status = "branch_created"

            # Add message
            message = AIMessage(
                content=f"✅ Feature branch created successfully\n"
                f"- Branch: {state.feature_branch}\n"
                f"- Base: {state.base_branch}\n"
                f"- Next: Install dependencies"
            )
            state.messages.append(message)

            print(f"✅ Feature branch '{state.feature_branch}' created successfully")

        else:
            # Handle error - check if it's just branch already exists
            error_msg = result_data.get("message", "Unknown error creating branch")

            if "already exists" in error_msg:
                # Branch already exists - try to checkout to it instead
                print(
                    f"⚠️ Branch already exists, attempting to checkout: {state.feature_branch}"
                )

                # For now, just continue with existing branch
                state.current_branch = state.feature_branch
                state.current_phase = "install_dependencies"
                state.status = "branch_ready"

                # Add warning message
                message = AIMessage(
                    content=f"⚠️ Branch already exists, using existing branch\n"
                    f"- Branch: {state.feature_branch}\n"
                    f"- Next: Install dependencies"
                )
                state.messages.append(message)

                print(f"✅ Using existing branch '{state.feature_branch}'")

            else:
                # Real error - fail the workflow
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
