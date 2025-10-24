"""
Unit tests for Daytona adapters (Filesystem and Git).

Tests both LocalAdapters and DaytonaAdapters to ensure:
1. LocalAdapters work correctly (backward compatibility)
2. DaytonaAdapters properly mock sandbox operations
3. Factory functions return correct adapter based on config
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from agents.developer.daytona.adapters.filesystem_adapter import (
    LocalFilesystemAdapter,
    DaytonaFilesystemAdapter,
    get_filesystem_adapter
)
from agents.developer.daytona.adapters.git_adapter import (
    LocalGitAdapter,
    DaytonaGitAdapter,
    get_git_adapter
)


# ============================================================================
# LocalFilesystemAdapter Tests
# ============================================================================

class TestLocalFilesystemAdapter:
    """Test LocalFilesystemAdapter operations."""
    
    def test_read_file(self, temp_working_directory, sample_file_content):
        """Test reading a file with LocalFilesystemAdapter."""
        # Setup
        adapter = LocalFilesystemAdapter()
        test_file = temp_working_directory / "test.py"
        test_file.write_text(sample_file_content)
        
        # Execute
        result = adapter.read_file(
            file_path="test.py",
            start_line=None,
            end_line=None,
            working_directory=str(temp_working_directory)
        )
        
        # Verify
        assert "def hello_world():" in result
        assert "print(\"Hello, World!\")" in result
        # Should include line numbers (cat -n format)
        assert "1\t" in result or "     1" in result
    
    def test_read_file_with_line_range(self, temp_working_directory, sample_file_content):
        """Test reading specific line range from file."""
        # Setup
        adapter = LocalFilesystemAdapter()
        test_file = temp_working_directory / "test.py"
        test_file.write_text(sample_file_content)
        
        # Execute - read lines 1-2
        result = adapter.read_file(
            file_path="test.py",
            start_line=1,
            end_line=2,
            working_directory=str(temp_working_directory)
        )
        
        # Verify
        assert "def hello_world():" in result
        assert "return True" not in result  # Line 3, should not be included
    
    def test_write_file(self, temp_working_directory):
        """Test writing a file with LocalFilesystemAdapter."""
        # Setup
        adapter = LocalFilesystemAdapter()
        content = "print('Hello from test')"
        
        # Execute
        result = adapter.write_file(
            file_path="new_file.py",
            content=content,
            working_directory=str(temp_working_directory),
            create_dirs=True
        )
        
        # Verify
        assert "successfully" in result.lower()
        created_file = temp_working_directory / "new_file.py"
        assert created_file.exists()
        assert created_file.read_text() == content
    
    def test_write_file_with_subdirectory(self, temp_working_directory):
        """Test writing file in subdirectory with create_dirs=True."""
        # Setup
        adapter = LocalFilesystemAdapter()
        content = "test content"
        
        # Execute
        result = adapter.write_file(
            file_path="subdir/nested/file.txt",
            content=content,
            working_directory=str(temp_working_directory),
            create_dirs=True
        )
        
        # Verify
        assert "successfully" in result.lower()
        created_file = temp_working_directory / "subdir" / "nested" / "file.txt"
        assert created_file.exists()
        assert created_file.read_text() == content
    
    def test_list_files(self, temp_working_directory):
        """Test listing files in directory."""
        # Setup
        adapter = LocalFilesystemAdapter()
        
        # Create test files
        (temp_working_directory / "file1.py").write_text("content1")
        (temp_working_directory / "file2.py").write_text("content2")
        (temp_working_directory / "subdir").mkdir()
        (temp_working_directory / "subdir" / "file3.py").write_text("content3")
        
        # Execute
        result = adapter.list_files(
            directory_path=".",
            working_directory=str(temp_working_directory)
        )
        
        # Verify
        assert "file1.py" in result
        assert "file2.py" in result
        assert "subdir" in result
    
    def test_create_directory(self, temp_working_directory):
        """Test creating directory."""
        # Setup
        adapter = LocalFilesystemAdapter()
        
        # Execute
        result = adapter.create_directory(
            directory_path="new_dir/nested",
            working_directory=str(temp_working_directory)
        )
        
        # Verify
        assert "successfully" in result.lower() or "created" in result.lower()
        created_dir = temp_working_directory / "new_dir" / "nested"
        assert created_dir.exists()
        assert created_dir.is_dir()
    
    def test_security_check_path_traversal(self, temp_working_directory):
        """Test that path traversal attacks are prevented."""
        # Setup
        adapter = LocalFilesystemAdapter()
        
        # Execute & Verify - should raise error or return error message
        with pytest.raises(Exception):
            adapter.read_file(
                file_path="../../../etc/passwd",
                start_line=None,
                end_line=None,
                working_directory=str(temp_working_directory)
            )


# ============================================================================
# DaytonaFilesystemAdapter Tests
# ============================================================================

class TestDaytonaFilesystemAdapter:
    """Test DaytonaFilesystemAdapter operations with mocked sandbox."""
    
    def test_read_file(self, mock_sandbox_manager, mock_sandbox):
        """Test reading file from Daytona sandbox."""
        # Setup
        adapter = DaytonaFilesystemAdapter(mock_sandbox_manager)
        mock_sandbox.fs.download_file.return_value = b"def test():\n    pass\n"
        
        # Execute
        result = adapter.read_file(
            file_path="test.py",
            start_line=None,
            end_line=None,
            working_directory="/root/workspace/repo"
        )
        
        # Verify
        assert "def test():" in result
        mock_sandbox.fs.download_file.assert_called_once()
    
    def test_write_file(self, mock_sandbox_manager, mock_sandbox):
        """Test writing file to Daytona sandbox."""
        # Setup
        adapter = DaytonaFilesystemAdapter(mock_sandbox_manager)
        content = "print('test')"
        
        # Execute
        result = adapter.write_file(
            file_path="new_file.py",
            content=content,
            working_directory="/root/workspace/repo",
            create_dirs=True
        )
        
        # Verify
        assert "successfully" in result.lower()
        mock_sandbox.fs.upload_file.assert_called_once()
    
    def test_path_resolution(self, mock_sandbox_manager):
        """Test sandbox path resolution."""
        # Setup
        adapter = DaytonaFilesystemAdapter(mock_sandbox_manager)
        
        # Test relative path resolution
        resolved = adapter._resolve_sandbox_path("./app/main.py")
        assert resolved.startswith("/root/workspace/repo")
        
        # Test absolute path (should use as-is)
        resolved_abs = adapter._resolve_sandbox_path("/root/workspace/repo/app/main.py")
        assert resolved_abs == "/root/workspace/repo/app/main.py"
    
    def test_error_handling(self, mock_sandbox_manager, mock_sandbox):
        """Test graceful error handling when sandbox operations fail."""
        # Setup
        adapter = DaytonaFilesystemAdapter(mock_sandbox_manager)
        mock_sandbox.fs.download_file.side_effect = Exception("Sandbox connection failed")
        
        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            adapter.read_file(
                file_path="test.py",
                start_line=None,
                end_line=None,
                working_directory="/root/workspace/repo"
            )
        
        assert "Sandbox connection failed" in str(exc_info.value) or "Failed to read file" in str(exc_info.value)


# ============================================================================
# LocalGitAdapter Tests
# ============================================================================

class TestLocalGitAdapter:
    """Test LocalGitAdapter operations."""
    
    def test_create_branch(self, temp_git_repo):
        """Test creating a new branch with LocalGitAdapter."""
        # Setup
        adapter = LocalGitAdapter()
        
        # Execute
        result = adapter.create_branch(
            branch_name="feature/test-branch",
            base_branch="main",
            source_branch=None,
            working_directory=str(temp_git_repo)
        )
        
        # Verify
        assert result["success"] is True
        assert result["branch"] == "feature/test-branch"
        
        # Verify branch exists in git
        from git import Repo
        repo = Repo(temp_git_repo)
        assert "feature/test-branch" in [b.name for b in repo.branches]
    
    def test_commit(self, temp_git_repo):
        """Test committing changes with LocalGitAdapter."""
        # Setup
        adapter = LocalGitAdapter()
        
        # Create a change
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('test')")
        
        # Execute
        result = adapter.commit(
            message="feat: Add test file",
            working_directory=str(temp_git_repo)
        )
        
        # Verify
        assert result["success"] is True
        assert "commit" in result
        
        # Verify commit exists in git
        from git import Repo
        repo = Repo(temp_git_repo)
        latest_commit = repo.head.commit
        assert "Add test file" in latest_commit.message


# ============================================================================
# Factory Function Tests
# ============================================================================

class TestFactoryFunctions:
    """Test adapter factory functions."""
    
    def test_get_filesystem_adapter_local_mode(self, mock_env_daytona_disabled):
        """Test factory returns LocalFilesystemAdapter when Daytona disabled."""
        # Execute
        adapter = get_filesystem_adapter()
        
        # Verify
        assert isinstance(adapter, LocalFilesystemAdapter)
    
    @patch('agents.developer.daytona.adapters.filesystem_adapter.get_sandbox_manager')
    def test_get_filesystem_adapter_daytona_mode(self, mock_get_manager, mock_env_daytona_enabled, mock_sandbox_manager):
        """Test factory returns DaytonaFilesystemAdapter when Daytona enabled."""
        # Setup
        mock_get_manager.return_value = mock_sandbox_manager
        
        # Execute
        adapter = get_filesystem_adapter()
        
        # Verify
        assert isinstance(adapter, DaytonaFilesystemAdapter)
    
    def test_get_git_adapter_local_mode(self, mock_env_daytona_disabled):
        """Test factory returns LocalGitAdapter when Daytona disabled."""
        # Execute
        adapter = get_git_adapter()
        
        # Verify
        assert isinstance(adapter, LocalGitAdapter)
    
    @patch('agents.developer.daytona.adapters.git_adapter.get_sandbox_manager')
    def test_get_git_adapter_daytona_mode(self, mock_get_manager, mock_env_daytona_enabled, mock_sandbox_manager):
        """Test factory returns DaytonaGitAdapter when Daytona enabled."""
        # Setup
        mock_get_manager.return_value = mock_sandbox_manager
        
        # Execute
        adapter = get_git_adapter()
        
        # Verify
        assert isinstance(adapter, DaytonaGitAdapter)

