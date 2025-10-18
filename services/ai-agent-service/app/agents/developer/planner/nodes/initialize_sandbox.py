"""
Initialize Sandbox Node

Khởi tạo Daytona sandbox và clone GitHub repository để phân tích codebase.
"""

import asyncio
import os
import threading
from urllib.parse import urlparse

from daytona import AsyncDaytona, CreateSandboxFromImageParams, DaytonaConfig, Image
from langchain_core.messages import AIMessage

from ..state import PlannerState


async def _initialize_sandbox_async(state: PlannerState) -> PlannerState:
    """
    Initialize Sandbox node - Khởi tạo Daytona sandbox và clone GitHub repository.

    Tasks:
    1. Kiểm tra xem có cần tạo sandbox không (github_repo_url provided)
    2. Khởi tạo Daytona client với credentials
    3. Tạo sandbox instance với appropriate configuration
    4. Clone GitHub repository vào sandbox
    5. Set codebase_path từ sandbox working directory + repo path
    6. Handle authentication cho private repositories
    7. Error handling cho sandbox creation failures

    Args:
        state: PlannerState với github_repo_url (optional)

    Returns:
        Updated PlannerState với sandbox_id và codebase_path
    """
    print("\n" + "=" * 80)
    print("🚀 INITIALIZE SANDBOX NODE - Daytona Sandbox Setup")
    print("=" * 80)

    try:
        # Skip sandbox initialization if no GitHub repo URL provided
        if not state.github_repo_url:
            print(
                "⏭️  No GitHub repository URL provided - skipping sandbox initialization"
            )
            print("   Using existing codebase_path or default local path")

            # Add AI message for tracking
            state.messages.append(
                AIMessage(
                    content="Skipped sandbox initialization - no GitHub repository URL provided"
                )
            )
            return state

        print(f"🎯 Initializing sandbox for repository: {state.github_repo_url}")

        # Extract repository name from URL for sandbox naming
        repo_name = extract_repo_name_from_url(state.github_repo_url)
        print(f"📁 Repository name: {repo_name}")

        # Initialize Daytona client
        daytona_config = get_daytona_config()
        print("🔧 Daytona client configured")

        async with AsyncDaytona(daytona_config) as daytona:
            print("🏗️  Creating Daytona sandbox...")

            # Create sandbox with appropriate configuration
            sandbox_params = CreateSandboxFromImageParams(
                name=f"planner-{repo_name}",
                image=Image.debian_slim("3.12"),  # Python 3.12 on Debian
                language="python",
                labels={
                    "purpose": "planner-agent",
                    "repository": repo_name,
                    "created_by": "planner_agent",
                },
                auto_stop_interval=30,  # Auto-stop after 30 minutes of inactivity
                auto_archive_interval=60,  # Auto-archive after 1 hour of being stopped
                # Don't auto-delete - let user manage lifecycle
            )

            sandbox = await daytona.create(
                sandbox_params, timeout=120
            )  # 2 minutes timeout
            print(f"✅ Sandbox created successfully: {sandbox.id}")

            # Update state with sandbox ID
            state.sandbox_id = sandbox.id

            # Get sandbox working directory
            work_dir = await sandbox.get_work_dir()
            print(f"📂 Sandbox working directory: {work_dir}")

            # Clone repository into sandbox
            repo_path = f"{work_dir}/{repo_name}"
            print(f"📥 Cloning repository to: {repo_path}")

            # Get GitHub credentials if available
            github_username = os.getenv("GITHUB_USERNAME")
            github_token = os.getenv("GITHUB_TOKEN")

            if github_username and github_token:
                print("🔐 Using GitHub authentication for private repository access")
                await sandbox.git.clone(
                    url=state.github_repo_url,
                    path=repo_path,
                    username=github_username,
                    password=github_token,
                )
            else:
                print("🌐 Cloning public repository (no authentication)")
                await sandbox.git.clone(url=state.github_repo_url, path=repo_path)

            print("✅ Repository cloned successfully")

            # Set codebase_path to the cloned repository path
            state.codebase_path = repo_path
            print(f"📍 Codebase path set to: {state.codebase_path}")

            # Verify repository was cloned correctly
            try:
                status = await sandbox.git.status(repo_path)
                print(f"📊 Repository status: On branch {status.current_branch}")
            except Exception as e:
                print(f"⚠️  Could not get repository status: {e}")

            # Add AI message for tracking
            state.messages.append(
                AIMessage(
                    content=f"Sandbox initialized successfully: {sandbox.id}\n"
                    f"Repository cloned: {state.github_repo_url}\n"
                    f"Codebase path: {state.codebase_path}"
                )
            )

            print("🎉 Sandbox initialization completed successfully")
            return state

    except Exception as e:
        error_msg = f"Failed to initialize sandbox: {str(e)}"
        print(f"❌ {error_msg}")

        # Set error state but don't fail completely - fallback to local analysis
        state.error_message = error_msg
        state.sandbox_id = ""  # Clear any partial sandbox ID

        # Add AI message for tracking
        state.messages.append(
            AIMessage(
                content=f"Sandbox initialization failed: {error_msg}\n"
                "Falling back to local codebase analysis"
            )
        )

        print("⚠️  Falling back to local codebase analysis")
        return state


def extract_repo_name_from_url(github_url: str) -> str:
    """
    Extract repository name from GitHub URL.

    Examples:
    - https://github.com/user/repo.git -> repo
    - https://github.com/user/repo -> repo
    - git@github.com:user/repo.git -> repo
    """
    try:
        if github_url.startswith("git@"):
            # SSH format: git@github.com:user/repo.git
            repo_part = github_url.split(":")[-1]
        else:
            # HTTPS format: https://github.com/user/repo.git
            parsed = urlparse(github_url)
            repo_part = parsed.path.lstrip("/")

        # Remove .git suffix if present
        if repo_part.endswith(".git"):
            repo_part = repo_part[:-4]

        # Get just the repository name (last part after /)
        repo_name = repo_part.split("/")[-1]

        # Sanitize for use as sandbox name (alphanumeric and hyphens only)
        repo_name = "".join(c if c.isalnum() or c == "-" else "-" for c in repo_name)
        repo_name = repo_name.strip("-").lower()

        return repo_name or "unknown-repo"

    except Exception:
        return "unknown-repo"


def get_daytona_config() -> DaytonaConfig:
    """
    Get Daytona configuration from environment variables.

    Required environment variables:
    - DAYTONA_API_KEY: API key for authentication
    - DAYTONA_API_URL: API URL (defaults to https://app.daytona.io/api)
    - DAYTONA_TARGET: Target runner location (defaults to 'us')

    Optional for GitHub authentication:
    - GITHUB_USERNAME: GitHub username for private repos
    - GITHUB_TOKEN: GitHub token/password for private repos
    """
    api_key = os.getenv("DAYTONA_API_KEY")
    if not api_key:
        raise ValueError(
            "DAYTONA_API_KEY environment variable is required for sandbox initialization"
        )

    api_url = os.getenv("DAYTONA_API_URL", "https://app.daytona.io/api")
    target = os.getenv("DAYTONA_TARGET", "us")

    return DaytonaConfig(api_key=api_key, api_url=api_url, target=target)


def initialize_sandbox(state: PlannerState) -> PlannerState:
    """
    Synchronous wrapper for initialize_sandbox node.

    LangGraph requires synchronous nodes, so this wrapper runs the async
    implementation in a separate thread to avoid event loop conflicts.

    Args:
        state: PlannerState với github_repo_url (optional)

    Returns:
        Updated PlannerState với sandbox_id và codebase_path
    """
    result = None
    exception = None

    def run_in_thread():
        nonlocal result, exception
        try:
            # Create a new event loop for this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result = new_loop.run_until_complete(_initialize_sandbox_async(state))
            finally:
                new_loop.close()
        except Exception as e:
            exception = e

    # Run async function in a separate thread
    thread = threading.Thread(target=run_in_thread, daemon=False)
    thread.start()
    thread.join()

    if exception:
        raise exception from None
    return result
