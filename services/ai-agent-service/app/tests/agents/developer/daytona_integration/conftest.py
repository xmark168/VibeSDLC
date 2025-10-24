"""
Pytest fixtures for Daytona integration tests.

Provides mock objects and utilities for testing Daytona sandbox integration.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from git import Repo


@pytest.fixture
def mock_daytona_config():
    """
    Mock DaytonaConfig object for testing.

    Returns:
        Mock DaytonaConfig with test configuration
    """
    from agents.developer.daytona_integration.config import DaytonaConfig

    config = DaytonaConfig(
        api_key="test_api_key_123",
        api_url="http://localhost:3000/api",
        organization_id="test_org_id",
        target="us",
        enabled=True,
        sandbox_language="node",
        sandbox_snapshot="node",
        workspace_path="/root/workspace",
    )
    return config


@pytest.fixture
def mock_daytona_config_disabled():
    """
    Mock DaytonaConfig with enabled=False for local mode testing.

    Returns:
        None (simulating DaytonaConfig.from_env() returning None)
    """
    return None


@pytest.fixture
def mock_sandbox():
    """
    Mock Daytona sandbox object with fs and git APIs.

    Returns:
        Mock sandbox with mocked fs and git operations
    """
    sandbox = MagicMock()

    # Mock filesystem operations
    sandbox.fs.download_file.return_value = b"test file content"
    sandbox.fs.upload_file.return_value = {"status": "success"}
    sandbox.fs.list_files.return_value = {
        "files": [
            {"name": "file1.py", "type": "file"},
            {"name": "file2.py", "type": "file"},
            {"name": "dir1", "type": "directory"},
        ]
    }
    sandbox.fs.create_directory.return_value = {"status": "success"}

    # Mock git operations
    sandbox.git.clone.return_value = {"status": "success"}
    sandbox.git.checkout.return_value = {"status": "success"}
    sandbox.git.commit.return_value = {"status": "success", "commit_hash": "abc123"}
    sandbox.git.push.return_value = {"status": "success"}

    return sandbox


@pytest.fixture
def mock_sandbox_manager(mock_sandbox):
    """
    Mock SandboxManager for testing.

    Args:
        mock_sandbox: Mock sandbox fixture

    Returns:
        Mock SandboxManager with mocked methods
    """
    manager = MagicMock()

    # Mock sandbox lifecycle methods
    manager.create_sandbox.return_value = {
        "sandbox_id": "test_sandbox_123",
        "workspace_path": "/root/workspace",
        "status": "created",
    }
    manager.get_sandbox.return_value = mock_sandbox
    manager.is_sandbox_active.return_value = True
    manager.get_workspace_path.return_value = "/root/workspace/repo"
    manager.cleanup_sandbox.return_value = {
        "status": "deleted",
        "sandbox_id": "test_sandbox_123",
    }
    manager.sandbox_id = "test_sandbox_123"

    return manager


@pytest.fixture
def temp_git_repo() -> Generator[Path, None, None]:
    """
    Create a temporary git repository for testing.

    Yields:
        Path to temporary git repository
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repository
        repo = Repo.init(repo_path)

        # Configure git user
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create initial commit
        test_file = repo_path / "README.md"
        test_file.write_text("# Test Repository")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Add remote origin
        repo.create_remote("origin", "git@github.com:test/test-repo.git")

        yield repo_path


@pytest.fixture
def temp_working_directory() -> Generator[Path, None, None]:
    """
    Create a temporary working directory for testing.

    Yields:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_env_daytona_enabled(monkeypatch):
    """
    Set environment variables for Daytona enabled mode.

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    monkeypatch.setenv("DAYTONA_ENABLED", "true")
    monkeypatch.setenv("DAYTONA_API_KEY", "test_api_key_123")
    monkeypatch.setenv("DAYTONA_API_URL", "http://localhost:3000/api")
    monkeypatch.setenv("DAYTONA_ORGANIZATION_ID", "test_org_id")
    monkeypatch.setenv("DAYTONA_TARGET", "us")


@pytest.fixture
def mock_env_daytona_disabled(monkeypatch):
    """
    Set environment variables for Daytona disabled mode (local mode).

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    monkeypatch.setenv("DAYTONA_ENABLED", "false")
    # Remove other Daytona env vars if they exist
    monkeypatch.delenv("DAYTONA_API_KEY", raising=False)
    monkeypatch.delenv("DAYTONA_API_URL", raising=False)
    monkeypatch.delenv("DAYTONA_ORGANIZATION_ID", raising=False)


@pytest.fixture
def sample_file_content():
    """
    Sample file content for testing.

    Returns:
        String with sample Python code
    """
    return """def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
"""


@pytest.fixture
def sample_git_commit_data():
    """
    Sample git commit data for testing.

    Returns:
        Dictionary with commit information
    """
    return {
        "message": "feat: Add new feature",
        "author": "Test User <test@example.com>",
        "files": ["app/main.py", "app/utils.py"],
        "branch": "feature/test-branch",
    }
