"""
Setup Branch Node

Tạo feature branch cho implementation sử dụng Git tools.

REFACTORED: Now supports Daytona sandbox mode with automatic sandbox creation and repository cloning.
"""

import json

from langchain_core.messages import AIMessage

from ..state import GitOperation, ImplementorState
from ..tool.git_tools_gitpython import create_feature_branch_tool
from ..utils.validators import validate_git_operations


def setup_branch(state: ImplementorState) -> ImplementorState:
    """
    Tạo feature branch cho implementation.

    Supports both local mode and Daytona sandbox mode:
    - Local mode: Creates branch in local repository
    - Daytona mode: Creates sandbox, clones repository, then creates branch

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

        # Initialize Daytona sandbox if enabled
        working_dir = _initialize_daytona_sandbox(state, working_dir)

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


def _initialize_daytona_sandbox(state: ImplementorState, working_dir: str) -> str:
    """
    Initialize Daytona sandbox if enabled.

    This function:
    1. Detects Daytona mode from environment variables
    2. Creates sandbox if not already active
    3. Extracts repository URL from local .git/config
    4. Clones repository to sandbox workspace
    5. Updates state with sandbox information

    Args:
        state: ImplementorState to update with sandbox info
        working_dir: Current working directory (local path)

    Returns:
        Updated working directory (sandbox path if Daytona mode, otherwise original)
    """
    try:
        # Import Daytona utilities
        from ...daytona_integration.adapters import get_git_adapter
        from ...daytona_integration.config import DaytonaConfig
        from ...daytona_integration.sandbox_manager import get_sandbox_manager

        # Detect Daytona mode
        daytona_config = DaytonaConfig.from_env()

        if not daytona_config or not daytona_config.enabled:
            # Local mode: keep current behavior
            print("📍 Local mode: Using local filesystem")
            state.sandbox_mode = False
            state.original_codebase_path = working_dir
            return working_dir

        print("🚀 Daytona mode enabled: Initializing sandbox...")

        # Get sandbox manager
        sandbox_manager = get_sandbox_manager(daytona_config)

        # Create or get existing sandbox
        if not sandbox_manager.is_sandbox_active():
            print("📦 Creating new Daytona sandbox...")
            sandbox_info = sandbox_manager.create_sandbox()
            print(f"✅ Sandbox created: {sandbox_info['sandbox_id']}")

            # Update state with sandbox info
            state.sandbox_id = sandbox_info["sandbox_id"]
        else:
            print(f"♻️  Reusing existing sandbox: {sandbox_manager.sandbox_id}")
            state.sandbox_id = sandbox_manager.sandbox_id

        # Extract repository URL from local git config
        repo_url = _extract_repo_url(working_dir)
        if not repo_url:
            print("⚠️ Could not extract repository URL from local .git/config")
            print("🔄 Falling back to local mode")
            state.sandbox_mode = False
            state.original_codebase_path = working_dir
            return working_dir

        print(f"📡 Repository URL: {repo_url}")

        # Get sandbox workspace path
        sandbox_path = sandbox_manager.get_workspace_path("repo")
        print(f"📂 Sandbox workspace: {sandbox_path}")

        # Clone repository to sandbox
        print("🔄 Cloning repository to sandbox...")
        git_adapter = get_git_adapter()

        try:
            clone_result = git_adapter.clone(repo_url, sandbox_path)
            print("✅ Repository cloned successfully")

            # Update state
            state.sandbox_mode = True
            state.original_codebase_path = working_dir
            state.codebase_path = sandbox_path
            state.github_repo_url = repo_url

            print("✅ Daytona sandbox initialized successfully")
            print(f"   Sandbox ID: {state.sandbox_id}")
            print(f"   Workspace: {sandbox_path}")

            return sandbox_path

        except Exception as clone_error:
            print(f"❌ Failed to clone repository to sandbox: {clone_error}")
            print("🔄 Falling back to local mode")

            # Cleanup sandbox on clone failure
            try:
                sandbox_manager.cleanup_sandbox()
                print("🧹 Cleaned up failed sandbox")
            except:
                pass

            state.sandbox_mode = False
            state.sandbox_id = ""
            state.original_codebase_path = working_dir
            return working_dir

    except Exception as e:
        print(f"⚠️ Daytona sandbox initialization failed: {e}")
        print("🔄 Falling back to local mode")

        # Ensure state is set to local mode
        state.sandbox_mode = False
        state.sandbox_id = ""
        state.original_codebase_path = working_dir

        return working_dir


def _extract_repo_url(working_dir: str) -> str | None:
    """
    Extract repository URL from local .git/config using GitPython.

    Args:
        working_dir: Local repository directory

    Returns:
        Repository URL or None if not found
    """
    try:
        from git import Repo

        repo = Repo(working_dir)

        # Try to get origin remote URL
        if "origin" in repo.remotes:
            origin = repo.remote("origin")
            return origin.url

        # If no origin, try first available remote
        if repo.remotes:
            return repo.remotes[0].url

        return None

    except Exception as e:
        print(f"⚠️ Failed to extract repository URL: {e}")
        return None
