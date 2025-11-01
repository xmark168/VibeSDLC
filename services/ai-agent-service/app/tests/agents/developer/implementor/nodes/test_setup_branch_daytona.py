"""
Unit tests for Daytona sandbox initialization in setup_branch node.

Tests the _initialize_daytona_sandbox() and _extract_repo_url() helper functions
to ensure proper sandbox lifecycle management and error handling.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from git import Repo

from agents.developer.implementor.nodes.setup_branch import (
    _initialize_daytona_sandbox,
    _extract_repo_url
)
from agents.developer.implementor.state import ImplementorState


# ============================================================================
# Test _extract_repo_url()
# ============================================================================

class TestExtractRepoUrl:
    """Test repository URL extraction from git config."""
    
    def test_extract_repo_url_with_origin(self, temp_git_repo):
        """Test extracting URL when origin remote exists."""
        # Execute
        repo_url = _extract_repo_url(str(temp_git_repo))
        
        # Verify
        assert repo_url is not None
        assert "test-repo.git" in repo_url
        assert "github.com" in repo_url or "test/test-repo" in repo_url
    
    def test_extract_repo_url_without_origin(self, temp_working_directory):
        """Test extracting URL when origin doesn't exist but other remotes do."""
        # Setup - create repo with non-origin remote
        repo = Repo.init(temp_working_directory)
        repo.config_writer().set_value("user", "name", "Test").release()
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        
        # Create initial commit
        test_file = temp_working_directory / "README.md"
        test_file.write_text("test")
        repo.index.add(["README.md"])
        repo.index.commit("Initial")
        
        # Add non-origin remote
        repo.create_remote("upstream", "git@github.com:upstream/repo.git")
        
        # Execute
        repo_url = _extract_repo_url(str(temp_working_directory))
        
        # Verify - should use first available remote
        assert repo_url is not None
        assert "upstream/repo.git" in repo_url
    
    def test_extract_repo_url_no_remotes(self, temp_working_directory):
        """Test extracting URL when no remotes exist."""
        # Setup - create repo without remotes
        repo = Repo.init(temp_working_directory)
        repo.config_writer().set_value("user", "name", "Test").release()
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        
        # Create initial commit
        test_file = temp_working_directory / "README.md"
        test_file.write_text("test")
        repo.index.add(["README.md"])
        repo.index.commit("Initial")
        
        # Execute
        repo_url = _extract_repo_url(str(temp_working_directory))
        
        # Verify
        assert repo_url is None
    
    def test_extract_repo_url_invalid_repo(self, temp_working_directory):
        """Test extracting URL from non-git directory."""
        # Execute
        repo_url = _extract_repo_url(str(temp_working_directory))
        
        # Verify
        assert repo_url is None


# ============================================================================
# Test _initialize_daytona_sandbox()
# ============================================================================

class TestInitializeDaytonaSandbox:
    """Test Daytona sandbox initialization logic."""
    
    @patch('agents.developer.implementor.nodes.setup_branch.DaytonaConfig')
    def test_initialize_sandbox_local_mode(self, mock_config_class):
        """Test that local mode is used when Daytona config not found."""
        # Setup
        mock_config_class.from_env.return_value = None
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main"
        )
        working_dir = "/test/local/path"
        
        # Execute
        result_dir = _initialize_daytona_sandbox(state, working_dir)
        
        # Verify
        assert result_dir == working_dir  # Should return original path
        assert state.sandbox_mode is False
        assert state.original_codebase_path == working_dir
    
    @patch('agents.developer.implementor.nodes.setup_branch.DaytonaConfig')
    def test_initialize_sandbox_config_disabled(self, mock_config_class):
        """Test that local mode is used when Daytona is disabled."""
        # Setup
        mock_config = MagicMock()
        mock_config.enabled = False
        mock_config_class.from_env.return_value = mock_config
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main"
        )
        working_dir = "/test/local/path"
        
        # Execute
        result_dir = _initialize_daytona_sandbox(state, working_dir)
        
        # Verify
        assert result_dir == working_dir
        assert state.sandbox_mode is False
    
    @patch('agents.developer.implementor.nodes.setup_branch.get_git_adapter')
    @patch('agents.developer.implementor.nodes.setup_branch._extract_repo_url')
    @patch('agents.developer.implementor.nodes.setup_branch.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.setup_branch.DaytonaConfig')
    def test_initialize_sandbox_daytona_mode(
        self,
        mock_config_class,
        mock_get_manager,
        mock_extract_url,
        mock_get_adapter,
        mock_daytona_config,
        mock_sandbox_manager
    ):
        """Test successful sandbox initialization in Daytona mode."""
        # Setup
        mock_config_class.from_env.return_value = mock_daytona_config
        mock_get_manager.return_value = mock_sandbox_manager
        mock_extract_url.return_value = "git@github.com:test/repo.git"
        
        mock_git_adapter = MagicMock()
        mock_git_adapter.clone.return_value = {"status": "success"}
        mock_get_adapter.return_value = mock_git_adapter
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main"
        )
        working_dir = "/test/local/path"
        
        # Execute
        result_dir = _initialize_daytona_sandbox(state, working_dir)
        
        # Verify
        assert result_dir == "/root/workspace/repo"  # Sandbox path
        assert state.sandbox_mode is True
        assert state.sandbox_id == "test_sandbox_123"
        assert state.codebase_path == "/root/workspace/repo"
        assert state.original_codebase_path == working_dir
        assert state.github_repo_url == "git@github.com:test/repo.git"
        
        # Verify methods called
        mock_sandbox_manager.create_sandbox.assert_called_once()
        mock_git_adapter.clone.assert_called_once()
    
    @patch('agents.developer.implementor.nodes.setup_branch._extract_repo_url')
    @patch('agents.developer.implementor.nodes.setup_branch.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.setup_branch.DaytonaConfig')
    def test_initialize_sandbox_repo_url_extraction_failed(
        self,
        mock_config_class,
        mock_get_manager,
        mock_extract_url,
        mock_daytona_config,
        mock_sandbox_manager
    ):
        """Test fallback to local mode when repo URL extraction fails."""
        # Setup
        mock_config_class.from_env.return_value = mock_daytona_config
        mock_get_manager.return_value = mock_sandbox_manager
        mock_extract_url.return_value = None  # Extraction failed
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main"
        )
        working_dir = "/test/local/path"
        
        # Execute
        result_dir = _initialize_daytona_sandbox(state, working_dir)
        
        # Verify - should fallback to local mode
        assert result_dir == working_dir
        assert state.sandbox_mode is False
        assert state.original_codebase_path == working_dir
    
    @patch('agents.developer.implementor.nodes.setup_branch.get_git_adapter')
    @patch('agents.developer.implementor.nodes.setup_branch._extract_repo_url')
    @patch('agents.developer.implementor.nodes.setup_branch.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.setup_branch.DaytonaConfig')
    def test_initialize_sandbox_clone_failed(
        self,
        mock_config_class,
        mock_get_manager,
        mock_extract_url,
        mock_get_adapter,
        mock_daytona_config,
        mock_sandbox_manager
    ):
        """Test cleanup and fallback when git clone fails."""
        # Setup
        mock_config_class.from_env.return_value = mock_daytona_config
        mock_get_manager.return_value = mock_sandbox_manager
        mock_extract_url.return_value = "git@github.com:test/repo.git"
        
        mock_git_adapter = MagicMock()
        mock_git_adapter.clone.side_effect = Exception("Clone failed")
        mock_get_adapter.return_value = mock_git_adapter
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main"
        )
        working_dir = "/test/local/path"
        
        # Execute
        result_dir = _initialize_daytona_sandbox(state, working_dir)
        
        # Verify - should cleanup and fallback
        assert result_dir == working_dir
        assert state.sandbox_mode is False
        assert state.sandbox_id == ""
        
        # Verify cleanup was called
        mock_sandbox_manager.cleanup_sandbox.assert_called_once()
    
    @patch('agents.developer.implementor.nodes.setup_branch.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.setup_branch.DaytonaConfig')
    def test_initialize_sandbox_general_exception(
        self,
        mock_config_class,
        mock_get_manager,
        mock_daytona_config
    ):
        """Test graceful fallback on general exception."""
        # Setup
        mock_config_class.from_env.return_value = mock_daytona_config
        mock_get_manager.side_effect = Exception("Unexpected error")
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main"
        )
        working_dir = "/test/local/path"
        
        # Execute
        result_dir = _initialize_daytona_sandbox(state, working_dir)
        
        # Verify - should fallback gracefully
        assert result_dir == working_dir
        assert state.sandbox_mode is False
        assert state.sandbox_id == ""
    
    @patch('agents.developer.implementor.nodes.setup_branch.get_git_adapter')
    @patch('agents.developer.implementor.nodes.setup_branch._extract_repo_url')
    @patch('agents.developer.implementor.nodes.setup_branch.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.setup_branch.DaytonaConfig')
    def test_initialize_sandbox_reuse_existing(
        self,
        mock_config_class,
        mock_get_manager,
        mock_extract_url,
        mock_get_adapter,
        mock_daytona_config,
        mock_sandbox_manager
    ):
        """Test reusing existing sandbox instead of creating new one."""
        # Setup
        mock_config_class.from_env.return_value = mock_daytona_config
        mock_sandbox_manager.is_sandbox_active.return_value = True  # Sandbox already exists
        mock_get_manager.return_value = mock_sandbox_manager
        mock_extract_url.return_value = "git@github.com:test/repo.git"
        
        mock_git_adapter = MagicMock()
        mock_git_adapter.clone.return_value = {"status": "success"}
        mock_get_adapter.return_value = mock_git_adapter
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main"
        )
        working_dir = "/test/local/path"
        
        # Execute
        result_dir = _initialize_daytona_sandbox(state, working_dir)
        
        # Verify
        assert state.sandbox_mode is True
        assert state.sandbox_id == "test_sandbox_123"
        
        # Verify create_sandbox was NOT called (reusing existing)
        mock_sandbox_manager.create_sandbox.assert_not_called()

