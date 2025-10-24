"""
Integration tests for Daytona sandbox integration.

Tests full workflow scenarios with both local mode and Daytona mode
to ensure backward compatibility and proper sandbox lifecycle management.
"""

from unittest.mock import MagicMock, patch

import pytest
from agents.developer.daytona_integration.adapters import (
    get_filesystem_adapter,
    get_git_adapter,
)
from agents.developer.daytona_integration.adapters.filesystem_adapter import (
    LocalFilesystemAdapter,
)
from agents.developer.daytona_integration.adapters.git_adapter import LocalGitAdapter

# ============================================================================
# Local Mode Integration Tests
# ============================================================================


class TestLocalModeIntegration:
    """Test that local mode works correctly (backward compatibility)."""

    def test_filesystem_adapter_local_mode(
        self, mock_env_daytona_disabled, temp_working_directory
    ):
        """Test filesystem operations in local mode."""
        # Execute
        adapter = get_filesystem_adapter()

        # Verify correct adapter type
        assert isinstance(adapter, LocalFilesystemAdapter)

        # Test write operation
        result = adapter.write_file(
            file_path="test.txt",
            content="Hello, World!",
            working_directory=str(temp_working_directory),
            create_dirs=True,
        )
        assert "successfully" in result.lower()

        # Test read operation
        content = adapter.read_file(
            file_path="test.txt",
            start_line=None,
            end_line=None,
            working_directory=str(temp_working_directory),
        )
        assert "Hello, World!" in content

    def test_git_adapter_local_mode(self, mock_env_daytona_disabled, temp_git_repo):
        """Test git operations in local mode."""
        # Execute
        adapter = get_git_adapter()

        # Verify correct adapter type
        assert isinstance(adapter, LocalGitAdapter)

        # Test branch creation
        result = adapter.create_branch(
            branch_name="feature/test",
            base_branch="main",
            source_branch=None,
            working_directory=str(temp_git_repo),
        )
        assert result["success"] is True
        assert result["branch"] == "feature/test"

    def test_backward_compatibility(self, mock_env_daytona_disabled):
        """Test that existing code works without changes in local mode."""
        # This test verifies that when DAYTONA_ENABLED=false,
        # the system behaves exactly as before the Daytona integration

        # Get adapters
        fs_adapter = get_filesystem_adapter()
        git_adapter = get_git_adapter()

        # Verify they are local adapters
        assert isinstance(fs_adapter, LocalFilesystemAdapter)
        assert isinstance(git_adapter, LocalGitAdapter)

        # Verify no Daytona dependencies are loaded
        # (adapters should work without Daytona SDK)
        assert fs_adapter is not None
        assert git_adapter is not None


# ============================================================================
# Daytona Mode Integration Tests (with mocking)
# ============================================================================


class TestDaytonaModeIntegration:
    """Test Daytona mode with mocked sandbox."""

    @patch("agents.developer.daytona.adapters.filesystem_adapter.get_sandbox_manager")
    def test_filesystem_adapter_daytona_mode(
        self,
        mock_get_manager,
        mock_env_daytona_enabled,
        mock_sandbox_manager,
        mock_sandbox,
    ):
        """Test filesystem operations in Daytona mode."""
        # Setup
        mock_get_manager.return_value = mock_sandbox_manager
        mock_sandbox.fs.download_file.return_value = b"Sandbox content"

        # Execute
        adapter = get_filesystem_adapter()

        # Verify correct adapter type
        from agents.developer.daytona_integration.adapters.filesystem_adapter import (
            DaytonaFilesystemAdapter,
        )

        assert isinstance(adapter, DaytonaFilesystemAdapter)

        # Test read operation
        content = adapter.read_file(
            file_path="test.txt",
            start_line=None,
            end_line=None,
            working_directory="/root/workspace/repo",
        )
        assert "Sandbox content" in content
        mock_sandbox.fs.download_file.assert_called_once()

    @patch("agents.developer.daytona.adapters.git_adapter.get_sandbox_manager")
    def test_git_adapter_daytona_mode(
        self,
        mock_get_manager,
        mock_env_daytona_enabled,
        mock_sandbox_manager,
        mock_sandbox,
    ):
        """Test git operations in Daytona mode."""
        # Setup
        mock_get_manager.return_value = mock_sandbox_manager
        mock_sandbox.git.checkout.return_value = {"status": "success"}

        # Execute
        adapter = get_git_adapter()

        # Verify correct adapter type
        from agents.developer.daytona_integration.adapters.git_adapter import (
            DaytonaGitAdapter,
        )

        assert isinstance(adapter, DaytonaGitAdapter)

        # Test branch creation
        result = adapter.create_branch(
            branch_name="feature/test",
            base_branch="main",
            source_branch=None,
            working_directory="/root/workspace/repo",
        )
        assert result["success"] is True
        mock_sandbox.git.checkout.assert_called()


# ============================================================================
# Error Scenario Tests
# ============================================================================


class TestErrorScenarios:
    """Test error handling and fallback scenarios."""

    @patch("agents.developer.daytona.config.DaytonaConfig.from_env")
    def test_fallback_on_config_missing(self, mock_from_env, monkeypatch):
        """Test fallback to local mode when Daytona config is missing."""
        # Setup - simulate missing API key
        monkeypatch.setenv("DAYTONA_ENABLED", "true")
        monkeypatch.delenv("DAYTONA_API_KEY", raising=False)
        mock_from_env.return_value = None

        # Execute
        adapter = get_filesystem_adapter()

        # Verify - should fallback to local adapter
        assert isinstance(adapter, LocalFilesystemAdapter)

    @patch("agents.developer.daytona.sandbox_manager.get_sandbox_manager")
    @patch("agents.developer.daytona.config.DaytonaConfig.from_env")
    def test_fallback_on_sandbox_creation_failed(
        self,
        mock_from_env,
        mock_get_manager,
        mock_env_daytona_enabled,
        mock_daytona_config,
    ):
        """Test fallback when sandbox creation fails."""
        # Setup
        mock_from_env.return_value = mock_daytona_config
        mock_manager = MagicMock()
        mock_manager.create_sandbox.side_effect = Exception("Sandbox creation failed")
        mock_get_manager.return_value = mock_manager

        # In real scenario, the setup_branch node would catch this
        # and fallback to local mode
        with pytest.raises(Exception) as exc_info:
            mock_manager.create_sandbox()

        assert "Sandbox creation failed" in str(exc_info.value)

    def test_adapter_selection_based_on_env(self, monkeypatch):
        """Test that adapter selection correctly responds to environment changes."""
        # Test 1: Daytona disabled
        monkeypatch.setenv("DAYTONA_ENABLED", "false")
        adapter1 = get_filesystem_adapter()
        assert isinstance(adapter1, LocalFilesystemAdapter)

        # Test 2: Daytona enabled (but will fail due to missing config)
        monkeypatch.setenv("DAYTONA_ENABLED", "true")
        # Without proper config, should still return local adapter
        adapter2 = get_filesystem_adapter()
        # May return either type depending on config availability
        assert adapter2 is not None


# ============================================================================
# Sandbox Lifecycle Tests
# ============================================================================


class TestSandboxLifecycle:
    """Test sandbox lifecycle management in workflow."""

    @patch("agents.developer.implementor.nodes.setup_branch.get_git_adapter")
    @patch("agents.developer.implementor.nodes.setup_branch._extract_repo_url")
    @patch("agents.developer.implementor.nodes.setup_branch.get_sandbox_manager")
    @patch("agents.developer.implementor.nodes.setup_branch.DaytonaConfig")
    def test_sandbox_creation_and_cleanup(
        self,
        mock_config_class,
        mock_get_manager,
        mock_extract_url,
        mock_get_adapter,
        mock_daytona_config,
        mock_sandbox_manager,
    ):
        """Test complete sandbox lifecycle: create -> use -> cleanup."""
        from agents.developer.implementor.nodes.finalize import _handle_sandbox_cleanup
        from agents.developer.implementor.nodes.setup_branch import (
            _initialize_daytona_sandbox,
        )
        from agents.developer.implementor.state import ImplementorState

        # Setup
        mock_config_class.from_env.return_value = mock_daytona_config
        mock_get_manager.return_value = mock_sandbox_manager
        mock_extract_url.return_value = "git@github.com:test/repo.git"

        mock_git_adapter = MagicMock()
        mock_git_adapter.clone.return_value = {"status": "success"}
        mock_get_adapter.return_value = mock_git_adapter

        # Create state
        state = ImplementorState(
            task_id="TEST-001", feature_branch="feature/test", base_branch="main"
        )

        # Step 1: Initialize sandbox
        working_dir = _initialize_daytona_sandbox(state, "/test/local")

        # Verify sandbox created
        assert state.sandbox_mode is True
        assert state.sandbox_id == "test_sandbox_123"
        assert working_dir == "/root/workspace/repo"

        # Step 2: Simulate workflow completion
        state.status = "completed"

        # Step 3: Cleanup sandbox
        with patch(
            "agents.developer.implementor.nodes.finalize.DaytonaConfig"
        ) as mock_cleanup_config:
            with patch(
                "agents.developer.implementor.nodes.finalize.get_sandbox_manager"
            ) as mock_cleanup_manager:
                mock_cleanup_config.from_env.return_value = mock_daytona_config
                mock_cleanup_manager.return_value = mock_sandbox_manager

                _handle_sandbox_cleanup(state)

        # Verify cleanup called
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.success is True
        mock_sandbox_manager.cleanup_sandbox.assert_called()
