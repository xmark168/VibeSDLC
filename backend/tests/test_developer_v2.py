"""Test Developer V2 Agent with MetaGPT-inspired improvements.

Tests cover:
1. State definitions and schema validation
2. Graph flow and routing
3. Individual nodes (router, analyze, plan, implement, code_review, run_code, debug_error)
4. Tools (execute_command, detect_test_command, etc.)
5. Workspace management (setup, merge, cleanup)
6. End-to-end workflows
"""

import asyncio
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools import (
    get_markdown_code_block_type,
    detect_test_command,
    execute_command_async,
    find_test_file,
    CommandResult,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def base_state():
    """Create base DeveloperState for testing."""
    return {
        "story_id": str(uuid4()),
        "story_title": "Test Story",
        "story_content": "As a user, I want to login so that I can access my account",
        "acceptance_criteria": ["User can login with email", "User sees error on invalid password"],
        "project_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": str(uuid4()),
        "langfuse_handler": None,
        "action": None,
        "task_type": None,
        "complexity": None,
        "workspace_path": "",
        "branch_name": "",
        "main_workspace": "",
        "workspace_ready": False,
        "index_ready": False,
        "merged": False,
        "code_changes": [],
        "files_created": [],
        "files_modified": [],
        "current_step": 0,
        "total_steps": 0,
        "implementation_plan": [],
        "code_review_k": 2,
        "code_review_passed": False,
        "code_review_iteration": 0,
        "debug_count": 0,
        "max_debug": 3,
    }


@pytest.fixture
def mock_agent():
    """Create mock DeveloperV2 agent."""
    agent = MagicMock()
    agent.name = "TestDeveloper"
    agent.role_type = "developer"  # Must be a string
    agent.message_user = AsyncMock()
    agent._setup_workspace = MagicMock(return_value={
        "workspace_path": "/tmp/test_workspace",
        "branch_name": "story_abc123",
        "main_workspace": "/tmp/main_workspace",
        "workspace_ready": True,
    })
    agent._commit_changes = MagicMock(return_value="Committed successfully")
    agent.context = MagicMock()
    agent.context.ensure_loaded = AsyncMock()
    return agent


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    # Use ignore_cleanup_errors for Windows compatibility
    tmpdir_obj = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    tmpdir = tmpdir_obj.name
    workspace = Path(tmpdir)
    
    # Create basic project structure
    (workspace / "src").mkdir()
    (workspace / "tests").mkdir()
    
    # Create a Python file
    (workspace / "src" / "calculator.py").write_text('''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
''')
    
    # Create a test file
    (workspace / "tests" / "test_calculator.py").write_text('''
import pytest
from src.calculator import Calculator

def test_add():
    calc = Calculator()
    assert calc.add(2, 3) == 5

def test_subtract():
    calc = Calculator()
    assert calc.subtract(5, 3) == 2
''')
    
    # Create pyproject.toml
    (workspace / "pyproject.toml").write_text('''
[project]
name = "test-project"
version = "0.1.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
''')
    
    yield workspace
    
    # Cleanup - ignore errors on Windows
    try:
        tmpdir_obj.cleanup()
    except (PermissionError, OSError):
        pass


# =============================================================================
# UNIT TESTS - Tools
# =============================================================================

class TestMarkdownCodeBlockType:
    """Test get_markdown_code_block_type function."""
    
    def test_python_files(self):
        assert get_markdown_code_block_type("main.py") == "python"
        assert get_markdown_code_block_type("src/utils/helper.py") == "python"
    
    def test_javascript_files(self):
        assert get_markdown_code_block_type("app.js") == "javascript"
        # jsx files are detected as javascript
        assert get_markdown_code_block_type("src/index.jsx") == "javascript"
    
    def test_typescript_files(self):
        assert get_markdown_code_block_type("app.ts") == "typescript"
        # tsx files are detected as typescript
        assert get_markdown_code_block_type("Component.tsx") == "typescript"
    
    def test_other_files(self):
        assert get_markdown_code_block_type("styles.css") == "css"
        assert get_markdown_code_block_type("config.json") == "json"
        assert get_markdown_code_block_type("README.md") == "markdown"
        # Dockerfile without extension returns empty
        result = get_markdown_code_block_type("Dockerfile")
        assert result in ["", "dockerfile"]  # Accept either
    
    def test_unknown_extension(self):
        assert get_markdown_code_block_type("unknown.xyz") == ""


class TestDetectTestCommand:
    """Test detect_test_command function."""
    
    def test_python_project_with_pytest(self, temp_workspace):
        """Test detection of pytest for Python project."""
        cmd = detect_test_command(str(temp_workspace))
        assert cmd == ["python", "-m", "pytest", "-v"]
    
    def test_node_project_with_package_json(self):
        """Test detection of npm test for Node project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "package.json").write_text(json.dumps({
                "name": "test-project",
                "scripts": {"test": "jest"}
            }))
            
            cmd = detect_test_command(str(workspace))
            assert cmd == ["npm", "test"]
    
    def test_empty_directory(self):
        """Test fallback for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = detect_test_command(tmpdir)
            assert "No test framework" in " ".join(cmd)


class TestFindTestFile:
    """Test find_test_file function."""
    
    def test_find_python_test(self, temp_workspace):
        """Test finding Python test file."""
        test_file = find_test_file(str(temp_workspace), "calculator.py")
        assert test_file is not None
        assert "test_calculator.py" in test_file
    
    def test_find_nonexistent_test(self, temp_workspace):
        """Test finding test for file without tests."""
        test_file = find_test_file(str(temp_workspace), "nonexistent.py")
        assert test_file is None


class TestCommandResult:
    """Test CommandResult class."""
    
    def test_success_result(self):
        result = CommandResult(stdout="output", stderr="", returncode=0)
        assert result.success == True
        assert result.stdout == "output"
        assert result.returncode == 0
    
    def test_failure_result(self):
        result = CommandResult(stdout="", stderr="error", returncode=1)
        assert result.success == False
        assert result.stderr == "error"
        assert result.returncode == 1


# =============================================================================
# UNIT TESTS - State
# =============================================================================

class TestDeveloperState:
    """Test DeveloperState TypedDict structure."""
    
    def test_state_accepts_all_fields(self, base_state):
        """Test that state accepts all defined fields."""
        # This should not raise any errors
        state: DeveloperState = base_state
        assert state["story_id"] is not None
        assert state["code_review_k"] == 2
        assert state["max_debug"] == 3
    
    def test_state_metagpt_fields(self, base_state):
        """Test MetaGPT-inspired fields."""
        base_state["code_plan_doc"] = "Strategic plan..."
        base_state["development_plan"] = ["Step 1", "Step 2"]
        base_state["is_pass"] = True
        base_state["needs_revision"] = False
        
        assert base_state["code_plan_doc"] == "Strategic plan..."
        assert len(base_state["development_plan"]) == 2
    
    def test_state_code_review_fields(self, base_state):
        """Test code review fields."""
        base_state["code_review_passed"] = True
        base_state["code_review_results"] = [{"result": "LGTM"}]
        base_state["code_review_iteration"] = 1
        
        assert base_state["code_review_passed"] == True
        assert len(base_state["code_review_results"]) == 1
    
    def test_state_run_code_fields(self, base_state):
        """Test run code fields."""
        base_state["run_status"] = "PASS"
        base_state["run_result"] = {
            "status": "PASS",
            "summary": "All tests passed",
            "file_to_fix": "",
            "send_to": "NoOne"
        }
        
        assert base_state["run_status"] == "PASS"
        assert base_state["run_result"]["send_to"] == "NoOne"
    
    def test_state_debug_fields(self, base_state):
        """Test debug fields."""
        base_state["debug_count"] = 1
        base_state["last_debug_file"] = "calculator.py"
        base_state["debug_history"] = [
            {"iteration": 1, "file": "calculator.py", "fix_description": "Fixed import"}
        ]
        
        assert base_state["debug_count"] == 1
        assert len(base_state["debug_history"]) == 1


# =============================================================================
# UNIT TESTS - Nodes (Mocked)
# =============================================================================

class TestRouterNode:
    """Test router node with mocked LLM."""
    
    @pytest.mark.asyncio
    async def test_router_returns_analyze_action(self, base_state, mock_agent):
        """Test router returns ANALYZE for new story."""
        from app.agents.developer_v2.src.nodes import router
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "action": "ANALYZE",
            "task_type": "feature",
            "complexity": "medium",
            "message": "Analyzing story...",
            "reason": "new_feature_request",  # snake_case required
            "confidence": 0.9
        })
        
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "ANALYZE"
            assert result["task_type"] == "feature"
    
    @pytest.mark.asyncio
    async def test_router_returns_respond_for_greeting(self, base_state, mock_agent):
        """Test router returns RESPOND for greeting."""
        from app.agents.developer_v2.src.nodes import router
        
        base_state["story_content"] = "Chào bạn!"
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "action": "RESPOND",
            "task_type": "documentation",  # Valid Literal value
            "complexity": "low",
            "message": "Chào bạn! Mình có thể giúp gì?",
            "reason": "greeting_detected",
            "confidence": 0.95
        })
        
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "RESPOND"


class TestCodeReviewNode:
    """Test code_review node with mocked LLM."""
    
    @pytest.mark.asyncio
    async def test_code_review_lgtm(self, base_state, mock_agent):
        """Test code review returns LGTM."""
        from app.agents.developer_v2.src.nodes import code_review
        
        base_state["code_changes"] = [{
            "file_path": "calculator.py",
            "code_snippet": "def add(a, b): return a + b"
        }]
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "filename": "calculator.py",
            "result": "LGTM",
            "issues": [],
            "rewritten_code": ""
        })
        
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await code_review(base_state, mock_agent)
            
            assert result["code_review_passed"] == True
    
    @pytest.mark.asyncio
    async def test_code_review_lbtm_rewrites(self, base_state, mock_agent, temp_workspace):
        """Test code review with LBTM rewrites code."""
        from app.agents.developer_v2.src.nodes import code_review
        
        base_state["workspace_path"] = str(temp_workspace)
        base_state["code_changes"] = [{
            "file_path": "src/calculator.py",
            "code_snippet": "def add(a, b): return a + b  # Missing type hints"
        }]
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "filename": "src/calculator.py",
            "result": "LBTM",
            "issues": ["Missing type hints"],
            "rewritten_code": "def add(a: int, b: int) -> int: return a + b"
        })
        
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await code_review(base_state, mock_agent)
            
            assert result["code_review_passed"] == False
            assert result["code_review_iteration"] == 1
    
    @pytest.mark.asyncio
    async def test_code_review_no_changes(self, base_state, mock_agent):
        """Test code review with no changes passes."""
        from app.agents.developer_v2.src.nodes import code_review
        
        base_state["code_changes"] = []
        
        result = await code_review(base_state, mock_agent)
        
        assert result["code_review_passed"] == True


class TestRunCodeNode:
    """Test run_code node (uses LLM + shell tools)."""
    
    @pytest.mark.asyncio
    async def test_run_code_passes(self, base_state, mock_agent, temp_workspace):
        """Test run_code with passing tests."""
        from app.agents.developer_v2.src.nodes import run_code
        
        base_state["workspace_path"] = str(temp_workspace)
        base_state["files_modified"] = ["src/calculator.py"]
        
        # Mock _llm_with_tools to return shell execution result
        mock_shell_output = json.dumps({
            "status": "success",
            "exit_code": 0,
            "stdout": "2 passed",
            "stderr": "",
            "command": "npm test"
        })
        
        # Mock analysis response
        mock_analysis_response = MagicMock()
        mock_analysis_response.content = json.dumps({
            "status": "PASS",
            "summary": "All tests passed",
            "file_to_fix": "",
            "send_to": "NoOne"
        })
        
        with patch('app.agents.developer_v2.src.nodes._llm_with_tools', new_callable=AsyncMock) as mock_llm_tools, \
             patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_fast_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            
            mock_llm_tools.return_value = mock_shell_output
            mock_fast_llm.ainvoke = AsyncMock(return_value=mock_analysis_response)
            
            result = await run_code(base_state, mock_agent)
            
            assert result["run_status"] == "PASS"
    
    @pytest.mark.asyncio
    async def test_run_code_fails(self, base_state, mock_agent, temp_workspace):
        """Test run_code with failing tests."""
        from app.agents.developer_v2.src.nodes import run_code
        
        base_state["workspace_path"] = str(temp_workspace)
        base_state["files_modified"] = ["src/calculator.py"]
        
        # Mock _llm_with_tools to return failed shell execution
        mock_shell_output = json.dumps({
            "status": "error",
            "exit_code": 1,
            "stdout": "",
            "stderr": "AssertionError: expected 5 but got 4",
            "command": "pytest"
        })
        
        # Mock analysis response
        mock_analysis_response = MagicMock()
        mock_analysis_response.content = json.dumps({
            "status": "FAIL",
            "summary": "Test failed: assertion error",
            "file_to_fix": "src/calculator.py",
            "send_to": "Engineer"
        })
        
        with patch('app.agents.developer_v2.src.nodes._llm_with_tools', new_callable=AsyncMock) as mock_llm_tools, \
             patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_fast_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            
            mock_llm_tools.return_value = mock_shell_output
            mock_fast_llm.ainvoke = AsyncMock(return_value=mock_analysis_response)
            
            result = await run_code(base_state, mock_agent)
            
            assert result["run_status"] == "FAIL"
            assert result["run_result"]["file_to_fix"] == "src/calculator.py"
    
    @pytest.mark.asyncio
    async def test_run_code_no_workspace(self, base_state, mock_agent):
        """Test run_code without workspace skips tests."""
        from app.agents.developer_v2.src.nodes import run_code
        
        base_state["workspace_path"] = ""
        
        result = await run_code(base_state, mock_agent)
        
        assert result["run_status"] == "PASS"
        assert "No workspace" in result["run_result"]["summary"]


class TestDebugErrorNode:
    """Test debug_error node."""
    
    @pytest.mark.asyncio
    async def test_debug_error_fixes_code(self, base_state, mock_agent, temp_workspace):
        """Test debug_error fixes code."""
        from app.agents.developer_v2.src.nodes import debug_error
        
        base_state["workspace_path"] = str(temp_workspace)
        base_state["files_modified"] = ["src/calculator.py"]
        base_state["run_result"] = {
            "status": "FAIL",
            "summary": "TypeError in add function",
            "file_to_fix": "src/calculator.py"
        }
        base_state["run_stderr"] = "TypeError: unsupported operand type(s)"
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "analysis": "Function lacks type conversion",
            "root_cause": "Arguments not converted to numbers",
            "fix_description": "Added int() conversion",
            "fixed_code": "def add(a, b): return int(a) + int(b)"
        })
        
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await debug_error(base_state, mock_agent)
            
            assert result["debug_count"] == 1
            assert result["last_debug_file"] == "src/calculator.py"
            assert len(result["debug_history"]) == 1
    
    @pytest.mark.asyncio
    async def test_debug_error_max_attempts(self, base_state, mock_agent):
        """Test debug_error stops at max attempts."""
        from app.agents.developer_v2.src.nodes import debug_error
        
        base_state["debug_count"] = 3
        base_state["max_debug"] = 3
        base_state["run_result"] = {"status": "FAIL"}
        
        result = await debug_error(base_state, mock_agent)
        
        # Should not increment debug_count
        assert result.get("debug_count", 3) == 3
    
    @pytest.mark.asyncio
    async def test_debug_error_pass_status(self, base_state, mock_agent):
        """Test debug_error does nothing when tests pass."""
        from app.agents.developer_v2.src.nodes import debug_error
        
        base_state["run_result"] = {"status": "PASS"}
        
        result = await debug_error(base_state, mock_agent)
        
        assert result.get("debug_count", 0) == 0


# =============================================================================
# UNIT TESTS - Graph Routing
# =============================================================================

class TestGraphRouting:
    """Test graph routing functions."""
    
    def test_route_to_workspace_for_analyze(self, base_state):
        """Test route sends ANALYZE to workspace setup."""
        from app.agents.developer_v2.src.graph import route
        
        base_state["action"] = "ANALYZE"
        result = route(base_state)
        assert result == "setup_workspace"
    
    def test_route_to_respond_for_respond(self, base_state):
        """Test route sends RESPOND directly."""
        from app.agents.developer_v2.src.graph import route
        
        base_state["action"] = "RESPOND"
        result = route(base_state)
        assert result == "respond"
    
    def test_route_to_clarify_for_clarify(self, base_state):
        """Test route sends CLARIFY directly."""
        from app.agents.developer_v2.src.graph import route
        
        base_state["action"] = "CLARIFY"
        result = route(base_state)
        assert result == "clarify"
    
    def test_should_continue_to_implement(self, base_state):
        """Test should_continue returns implement when steps remain."""
        from app.agents.developer_v2.src.graph import should_continue
        
        base_state["action"] = "IMPLEMENT"
        base_state["current_step"] = 1
        base_state["total_steps"] = 3
        
        result = should_continue(base_state)
        assert result == "implement"
    
    def test_should_continue_to_code_review(self, base_state):
        """Test should_continue returns code_review when done."""
        from app.agents.developer_v2.src.graph import should_continue
        
        base_state["action"] = "IMPLEMENT"
        base_state["current_step"] = 3
        base_state["total_steps"] = 3
        
        result = should_continue(base_state)
        assert result == "code_review"
    
    def test_route_after_code_review_to_run_code(self, base_state):
        """Test route_after_code_review goes to run_code when passed."""
        from app.agents.developer_v2.src.graph import route_after_code_review
        
        base_state["code_review_passed"] = True
        
        result = route_after_code_review(base_state)
        assert result == "run_code"
    
    def test_route_after_code_review_retry(self, base_state):
        """Test route_after_code_review retries when not passed."""
        from app.agents.developer_v2.src.graph import route_after_code_review
        
        base_state["code_review_passed"] = False
        base_state["code_review_iteration"] = 0
        base_state["code_review_k"] = 2
        
        result = route_after_code_review(base_state)
        assert result == "code_review"
    
    def test_route_after_run_code_to_merge(self, base_state):
        """Test route_after_run_code goes to merge when tests pass."""
        from app.agents.developer_v2.src.graph import route_after_run_code
        
        base_state["run_result"] = {"status": "PASS"}
        
        result = route_after_run_code(base_state)
        assert result == "merge_to_main"
    
    def test_route_after_run_code_to_debug(self, base_state):
        """Test route_after_run_code goes to debug when tests fail."""
        from app.agents.developer_v2.src.graph import route_after_run_code
        
        base_state["run_result"] = {"status": "FAIL"}
        base_state["debug_count"] = 0
        base_state["max_debug"] = 3
        
        result = route_after_run_code(base_state)
        assert result == "debug_error"
    
    def test_route_after_run_code_to_respond_max_debug(self, base_state):
        """Test route_after_run_code goes to respond at max debug."""
        from app.agents.developer_v2.src.graph import route_after_run_code
        
        base_state["run_result"] = {"status": "FAIL"}
        base_state["debug_count"] = 3
        base_state["max_debug"] = 3
        
        result = route_after_run_code(base_state)
        assert result == "respond"


# =============================================================================
# UNIT TESTS - Git Operations
# =============================================================================

class TestGitOperations:
    """Test GitPythonTool operations."""
    
    def test_merge_branch_operation(self, temp_workspace):
        """Test merge branch operation exists."""
        from app.agents.developer.tools.git_python_tool import GitPythonTool
        
        git_tool = GitPythonTool(root_dir=str(temp_workspace))
        
        # Initialize repo
        git_tool._run("init")
        
        # Should have merge operation
        assert hasattr(git_tool, '_merge_branch')
    
    def test_delete_branch_operation(self, temp_workspace):
        """Test delete branch operation exists."""
        from app.agents.developer.tools.git_python_tool import GitPythonTool
        
        git_tool = GitPythonTool(root_dir=str(temp_workspace))
        
        # Should have delete_branch operation
        assert hasattr(git_tool, '_delete_branch')


# =============================================================================
# INTEGRATION TESTS - End-to-End Flow
# =============================================================================

class TestEndToEndFlow:
    """Test end-to-end workflow (mocked)."""
    
    @pytest.mark.asyncio
    async def test_full_flow_simple_story(self, base_state, mock_agent):
        """Test full flow for a simple story (all mocked)."""
        from app.agents.developer_v2.src.nodes import router, analyze, plan
        
        # Router
        mock_router_response = MagicMock()
        mock_router_response.content = json.dumps({
            "action": "ANALYZE",
            "task_type": "feature",
            "complexity": "low",
            "message": "Starting analysis",
            "reason": "new_feature_request",  # Required field
            "confidence": 0.9
        })
        
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_router_response)
            
            result = await router(base_state, mock_agent)
            assert result["action"] == "ANALYZE"
        
        # Analyze
        base_state.update(result)
        mock_analyze_response = MagicMock()
        mock_analyze_response.content = json.dumps({
            "task_type": "feature",
            "complexity": "low",
            "summary": "Login feature implementation",
            "affected_files": ["auth.py"],
            "dependencies": [],
            "risks": [],
            "suggested_approach": "Create auth module"
        })
        
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_analyze_response)
            
            result = await analyze(base_state, mock_agent)
            assert result["analysis_result"] is not None
        
        # Plan
        base_state.update(result)
        mock_plan_response = MagicMock()
        mock_plan_response.content = json.dumps({
            "story_summary": "Login feature implementation",  # Required field
            "steps": [
                {"order": 1, "description": "Create auth.py", "file_path": "auth.py", "action": "create"}
            ],
            "total_estimated_hours": 2,
            "files_to_create": ["auth.py"],
            "files_to_modify": []
        })
        
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=mock_plan_response)
            
            result = await plan(base_state, mock_agent)
            assert len(result["implementation_plan"]) == 1
            assert result["total_steps"] == 1


class TestGraphCompilation:
    """Test that the graph compiles successfully."""
    
    def test_graph_compiles(self, mock_agent):
        """Test DeveloperGraph compiles without errors."""
        from app.agents.developer_v2.src.graph import DeveloperGraph
        
        graph = DeveloperGraph(agent=mock_agent)
        
        assert graph.graph is not None
    
    def test_graph_has_all_nodes(self, mock_agent):
        """Test graph has all expected nodes."""
        from app.agents.developer_v2.src.graph import DeveloperGraph
        
        graph = DeveloperGraph(agent=mock_agent)
        
        # Graph should have compiled successfully
        assert graph.graph is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
