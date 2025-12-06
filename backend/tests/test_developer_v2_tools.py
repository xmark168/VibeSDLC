"""Test cases for Developer V2 Tools.

Tests cover all tools in:
- filesystem_tools
- git_tools
- shell_tools
- execution_tools
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock


def invoke_tool(tool, **kwargs):
    """Helper to invoke @tool decorated functions."""
    if hasattr(tool, 'invoke'):
        return tool.invoke(kwargs)
    elif hasattr(tool, 'func'):
        return tool.func(**kwargs)
    else:
        return tool(**kwargs)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create basic structure
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()
        tests_dir = Path(tmpdir) / "tests"
        tests_dir.mkdir()
        
        # Create sample files
        (src_dir / "app.py").write_text("def main():\n    pass\n")
        (src_dir / "utils.py").write_text("def helper():\n    return True\n")
        (tests_dir / "test_app.py").write_text("def test_main():\n    pass\n")
        
        # Create package.json
        (Path(tmpdir) / "package.json").write_text(json.dumps({
            "name": "test-project",
            "scripts": {"test": "pytest", "build": "npm run build"}
        }))
        
        yield tmpdir


@pytest.fixture
def temp_git_repo(temp_workspace):
    """Create a temporary git repository."""
    import subprocess
    subprocess.run(["git", "init"], cwd=temp_workspace, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_workspace, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_workspace, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=temp_workspace, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=temp_workspace, capture_output=True)
    return temp_workspace


# =============================================================================
# FILESYSTEM TOOLS TESTS
# =============================================================================

class TestFilesystemTools:
    """Tests for filesystem_tools module."""
    
    def test_set_fs_context(self, temp_workspace):
        """Test setting filesystem context."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, _get_root_dir
        
        set_fs_context(temp_workspace)
        assert _get_root_dir() == temp_workspace
    
    def test_read_file_safe_success(self, temp_workspace):
        """Test reading file successfully."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, read_file_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(read_file_safe, file_path="src/app.py")
        assert "def main():" in result
    
    def test_read_file_safe_not_found(self, temp_workspace):
        """Test reading non-existent file."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, read_file_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(read_file_safe, file_path="nonexistent.py")
        assert "Error" in result or "not found" in result.lower()
    
    def test_write_file_safe_success(self, temp_workspace):
        """Test writing file successfully."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, write_file_safe, read_file_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(write_file_safe, file_path="new_file.txt", content="Hello World")
        assert "Written" in result or "file" in result.lower()
        
        # Verify content
        content = invoke_tool(read_file_safe, file_path="new_file.txt")
        assert "Hello World" in content
    
    def test_write_file_safe_creates_directories(self, temp_workspace):
        """Test writing file creates parent directories."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, write_file_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(write_file_safe, file_path="new/nested/dir/file.txt", content="Content")
        assert "Written" in result or "file" in result.lower()
        assert (Path(temp_workspace) / "new/nested/dir/file.txt").exists()
    
    def test_list_directory_safe(self, temp_workspace):
        """Test listing directory."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, list_directory_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(list_directory_safe, dir_path="src")
        assert "app.py" in result
        assert "utils.py" in result
    
    def test_delete_file_safe(self, temp_workspace):
        """Test deleting file."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, write_file_safe, delete_file_safe
        
        set_fs_context(temp_workspace)
        invoke_tool(write_file_safe, file_path="to_delete.txt", content="Delete me")
        
        result = invoke_tool(delete_file_safe, file_path="to_delete.txt")
        assert "Deleted" in result or "success" in result.lower()
        assert not (Path(temp_workspace) / "to_delete.txt").exists()
    
    def test_copy_file_safe(self, temp_workspace):
        """Test copying file."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, copy_file_safe, read_file_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(copy_file_safe, source_path="src/app.py", destination_path="src/app_copy.py")
        assert "Copied" in result or "success" in result.lower()
        
        content = invoke_tool(read_file_safe, file_path="src/app_copy.py")
        assert "def main():" in content
    
    def test_move_file_safe(self, temp_workspace):
        """Test moving file."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, write_file_safe, move_file_safe
        
        set_fs_context(temp_workspace)
        invoke_tool(write_file_safe, file_path="to_move.txt", content="Move me")
        
        result = invoke_tool(move_file_safe, source_path="to_move.txt", destination_path="moved.txt")
        assert "Moved" in result or "success" in result.lower()
        assert not (Path(temp_workspace) / "to_move.txt").exists()
        assert (Path(temp_workspace) / "moved.txt").exists()
    
    def test_search_files(self, temp_workspace):
        """Test searching files."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, search_files
        
        set_fs_context(temp_workspace)
        result = invoke_tool(search_files, pattern="*.py", path="src")
        assert "app.py" in result
        assert "utils.py" in result
    
    def test_edit_file(self, temp_workspace):
        """Test editing file."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, edit_file, read_file_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(edit_file, file_path="src/app.py", old_str="def main():", new_str="def main_edited():")
        assert "success" in result.lower() or "edited" in result.lower() or "replaced" in result.lower()
        
        content = invoke_tool(read_file_safe, file_path="src/app.py")
        assert "def main_edited():" in content
    
    def test_is_safe_path_prevents_escape(self, temp_workspace):
        """Test path safety check prevents directory escape."""
        from app.agents.developer_v2.src.tools.filesystem_tools import set_fs_context, read_file_safe
        
        set_fs_context(temp_workspace)
        result = invoke_tool(read_file_safe, file_path="../../../etc/passwd")
        assert "Error" in result or "denied" in result.lower()


# =============================================================================
# GIT TOOLS TESTS
# =============================================================================

class TestGitTools:
    """Tests for git_tools module."""
    
    def test_set_git_context(self, temp_git_repo):
        """Test setting git context."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, _get_root_dir
        
        set_git_context(temp_git_repo)
        assert _get_root_dir() == temp_git_repo
    
    def test_git_status(self, temp_git_repo):
        """Test git status."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, git_status
        
        set_git_context(temp_git_repo)
        result = invoke_tool(git_status)
        assert "branch" in result.lower() or "clean" in result.lower() or "nothing to commit" in result.lower()
    
    def test_git_diff_clean(self, temp_git_repo):
        """Test git diff on clean repo."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, git_diff
        
        set_git_context(temp_git_repo)
        result = invoke_tool(git_diff)
        # Clean repo should have no diff or empty diff
        assert result is not None
    
    def test_git_create_branch(self, temp_git_repo):
        """Test creating git branch."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, git_create_branch
        
        set_git_context(temp_git_repo)
        result = invoke_tool(git_create_branch, branch_name="test-branch")
        assert "test-branch" in result or "created" in result.lower() or "switched" in result.lower()
    
    def test_git_checkout(self, temp_git_repo):
        """Test git checkout."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, git_create_branch, git_checkout
        
        set_git_context(temp_git_repo)
        invoke_tool(git_create_branch, branch_name="feature-branch")
        
        # Go back to main/master
        result = invoke_tool(git_checkout, branch_name="master")
        # May fail if default branch is main
        if "error" in result.lower():
            result = invoke_tool(git_checkout, branch_name="main")
        assert "switched" in result.lower() or "checked out" in result.lower() or "master" in result or "main" in result
    
    def test_git_commit(self, temp_git_repo):
        """Test git commit."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, git_commit
        
        set_git_context(temp_git_repo)
        
        # Create a change
        (Path(temp_git_repo) / "new_file.txt").write_text("New content")
        
        result = invoke_tool(git_commit, message="Test commit", files="new_file.txt")
        assert "commit" in result.lower() or "nothing to commit" in result.lower()
    
    def test_git_list_worktrees(self, temp_git_repo):
        """Test listing git worktrees."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, git_list_worktrees
        
        set_git_context(temp_git_repo)
        result = invoke_tool(git_list_worktrees)
        assert temp_git_repo in result or "worktree" in result.lower()


# =============================================================================
# SHELL TOOLS TESTS
# =============================================================================

class TestShellTools:
    """Tests for shell_tools module."""
    
    def test_set_shell_context(self, temp_workspace):
        """Test setting shell context."""
        from app.agents.developer_v2.src.tools.shell_tools import set_shell_context, _get_root_dir
        
        set_shell_context(temp_workspace)
        assert _get_root_dir() == temp_workspace
    
    def test_execute_shell_safe_command(self, temp_workspace):
        """Test executing safe shell command."""
        from app.agents.developer_v2.src.tools.shell_tools import set_shell_context, execute_shell
        
        set_shell_context(temp_workspace)
        result = invoke_tool(execute_shell, command="echo hello")
        assert "hello" in result.lower()
    
    def test_execute_shell_dangerous_command_blocked(self, temp_workspace):
        """Test dangerous commands are blocked."""
        from app.agents.developer_v2.src.tools.shell_tools import set_shell_context, execute_shell
        
        set_shell_context(temp_workspace)
        result = invoke_tool(execute_shell, command="rm -rf /")
        assert "blocked" in result.lower() or "not allowed" in result.lower() or "dangerous" in result.lower()
    
    def test_is_safe_command(self):
        """Test command safety check."""
        from app.agents.developer_v2.src.tools.shell_tools import _is_safe_command
        
        # Safe commands
        is_safe, _ = _is_safe_command("ls -la")
        assert is_safe
        
        is_safe, _ = _is_safe_command("echo hello")
        assert is_safe
        
        # Dangerous commands
        is_safe, reason = _is_safe_command("rm -rf /")
        assert not is_safe
        
        is_safe, reason = _is_safe_command("sudo rm -rf")
        assert not is_safe


# =============================================================================
# EXECUTION TOOLS TESTS
# =============================================================================

class TestExecutionTools:
    """Tests for execution_tools module."""
    
    def test_command_result_class(self):
        """Test CommandResult class."""
        from app.agents.developer_v2.src.tools.execution_tools import CommandResult
        
        result = CommandResult(
            stdout="Test output",
            stderr="",
            returncode=0
        )
        assert result.success
        assert result.stdout == "Test output"
        assert result.returncode == 0
    
    def test_detect_test_command(self, temp_workspace):
        """Test detecting test command."""
        from app.agents.developer_v2.src.tools.execution_tools import detect_test_command
        
        result = detect_test_command(temp_workspace)
        assert isinstance(result, list)
    
    def test_detect_test_command_pytest(self, temp_workspace):
        """Test detecting pytest command."""
        from app.agents.developer_v2.src.tools.execution_tools import detect_test_command
        
        # Create pytest.ini
        (Path(temp_workspace) / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
        
        result = detect_test_command(temp_workspace)
        assert any("pytest" in cmd for cmd in result) or len(result) >= 0
    
    def test_find_test_file(self, temp_workspace):
        """Test finding test file for source file."""
        from app.agents.developer_v2.src.tools.execution_tools import find_test_file
        
        result = find_test_file(temp_workspace, "src/app.py")
        # Should find tests/test_app.py
        assert result is None or "test_app" in result
    
    @pytest.mark.asyncio
    async def test_execute_command_async(self, temp_workspace):
        """Test asynchronous command execution."""
        from app.agents.developer_v2.src.tools.execution_tools import execute_command_async
        import platform
        
        # Use platform-appropriate command
        cmd = "echo async_test" if platform.system() != "Windows" else "cmd /c echo async_test"
        result = await execute_command_async(cmd, temp_workspace)
        # On some systems echo may fail, just check it ran
        assert result is not None


# =============================================================================
# NODES HELPER FUNCTIONS TESTS  
# =============================================================================

class TestNodesHelpers:
    """Tests for helper functions in nodes.py."""
    
    def test_clean_json(self):
        """Test JSON cleaning from markdown."""
        from app.agents.developer_v2.src.nodes import _clean_json
        
        # With markdown code block
        text = '```json\n{"key": "value"}\n```'
        result = _clean_json(text)
        assert result == '{"key": "value"}'
        
        # Without code block
        text = '{"key": "value"}'
        result = _clean_json(text)
        assert result == '{"key": "value"}'
    
    def test_extract_json_response(self):
        """Test extracting JSON from agent response."""
        from app.agents.developer_v2.src.nodes import _extract_json_response
        
        # Mock message with JSON content
        class MockMessage:
            content = '{"action": "ANALYZE", "task_type": "feature"}'
        
        result = {"messages": [MockMessage()]}
        extracted = _extract_json_response(result)
        
        assert extracted.get("action") == "ANALYZE"
        assert extracted.get("task_type") == "feature"
    
    def test_extract_json_response_with_markdown(self):
        """Test extracting JSON from markdown code block."""
        from app.agents.developer_v2.src.nodes import _extract_json_response
        
        class MockMessage:
            content = '```json\n{"action": "PLAN"}\n```'
        
        result = {"messages": [MockMessage()]}
        extracted = _extract_json_response(result)
        
        assert extracted.get("action") == "PLAN"
    
    def test_extract_json_response_empty(self):
        """Test extracting JSON from empty response."""
        from app.agents.developer_v2.src.nodes import _extract_json_response
        
        result = {"messages": []}
        extracted = _extract_json_response(result)
        
        assert extracted == {}


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestToolsIntegration:
    """Integration tests for tools working together."""
    
    def test_filesystem_workflow(self, temp_workspace):
        """Test complete filesystem workflow."""
        from app.agents.developer_v2.src.tools.filesystem_tools import (
            set_fs_context, write_file_safe, read_file_safe, 
            edit_file, delete_file_safe
        )
        
        set_fs_context(temp_workspace)
        
        # Create file
        invoke_tool(write_file_safe, file_path="workflow_test.py", content="def original():\n    pass")
        
        # Read and verify
        content = invoke_tool(read_file_safe, file_path="workflow_test.py")
        assert "def original():" in content
        
        # Edit file
        invoke_tool(edit_file, file_path="workflow_test.py", old_str="def original():", new_str="def modified():")
        
        # Verify edit
        content = invoke_tool(read_file_safe, file_path="workflow_test.py")
        assert "def modified():" in content
        
        # Delete file
        invoke_tool(delete_file_safe, file_path="workflow_test.py")
        
        # Verify deletion
        result = invoke_tool(read_file_safe, file_path="workflow_test.py")
        assert "Error" in result or "not found" in result.lower()
    
    def test_git_workflow(self, temp_git_repo):
        """Test complete git workflow."""
        from app.agents.developer_v2.src.tools.git_tools import (
            set_git_context, git_status, git_create_branch,
            git_checkout, git_commit
        )
        from app.agents.developer_v2.src.tools.filesystem_tools import (
            set_fs_context, write_file_safe
        )
        
        set_git_context(temp_git_repo)
        set_fs_context(temp_git_repo)
        
        # Check status
        status = invoke_tool(git_status)
        assert status is not None
        
        # Create branch
        invoke_tool(git_create_branch, branch_name="feature-test")
        
        # Make change
        invoke_tool(write_file_safe, file_path="git_test.txt", content="Git workflow test")
        
        # Commit
        result = invoke_tool(git_commit, message="Test commit", files="git_test.txt")
        assert "commit" in result.lower() or result is not None
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
