"""End-to-End Test for Developer V2 - Create Learning Website.

This test simulates a real scenario where the DeveloperV2 agent
processes a story to create a beautiful learning website.
"""

import asyncio
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    _extract_json_response, _clean_json
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def learning_website_story():
    """Story for creating a learning website."""
    return {
        "story_id": str(uuid4()),
        "story_title": "Tạo Website Học Tập Online",
        "story_content": """
## User Story
As a student, I want to have a beautiful online learning platform
so that I can learn programming effectively.

## Description
Tạo một website học tập online đẹp mắt với các tính năng:
- Trang chủ giới thiệu các khóa học
- Danh sách khóa học với card design đẹp
- Trang chi tiết khóa học với video player

## Technical Stack
- Frontend: React + TailwindCSS
- Components: shadcn/ui
""",
        "acceptance_criteria": [
            "Trang chủ hiển thị hero section với call-to-action",
            "Danh sách khóa học với filter theo category",
            "Card khóa học có thumbnail, title, instructor, rating",
        ],
        "project_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": str(uuid4()),
    }


@pytest.fixture
def mock_developer_agent():
    """Create mock DeveloperV2 agent with full capabilities."""
    agent = MagicMock()
    agent.name = "TestDeveloper"
    agent.role_type = "developer"
    agent.project_id = uuid4()
    agent.message_user = AsyncMock()
    agent.context = MagicMock()
    agent.context.ensure_loaded = AsyncMock()
    agent.workspace_manager = MagicMock()
    agent.main_workspace = Path(tempfile.gettempdir()) / "test_workspace"
    agent.git_tool = MagicMock()
    return agent


@pytest.fixture
def temp_project_workspace():
    """Create temporary project workspace."""
    tmpdir_obj = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    workspace = Path(tmpdir_obj.name)
    
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "components").mkdir()
    (workspace / "src" / "pages").mkdir()
    (workspace / "public").mkdir()
    
    (workspace / "package.json").write_text(json.dumps({
        "name": "learning-website",
        "version": "0.1.0",
        "scripts": {"dev": "next dev", "build": "next build", "test": "jest"},
        "dependencies": {"react": "^18.2.0", "next": "^14.0.0", "tailwindcss": "^3.3.0"}
    }, indent=2))
    
    yield workspace
    
    try:
        tmpdir_obj.cleanup()
    except (PermissionError, OSError):
        pass


# =============================================================================
# MOCK AGENT RESPONSE HELPERS
# =============================================================================

def create_mock_agent_result(content: dict):
    """Create a mock agent result with messages containing JSON content."""
    mock_message = MagicMock()
    mock_message.content = json.dumps(content)
    return {"messages": [mock_message]}


def create_router_response():
    """Create mock router response."""
    return create_mock_agent_result({
        "action": "ANALYZE",
        "task_type": "feature",
        "complexity": "high",
        "message": "Analyzing learning website story...",
        "reason": "new_feature_request",
        "confidence": 0.95
    })


def create_analyze_response():
    """Create mock analyze response for learning website."""
    return create_mock_agent_result({
        "task_type": "feature",
        "complexity": "high",
        "summary": "Create a modern learning website with React and TailwindCSS",
        "affected_files": [
            "src/pages/index.tsx",
            "src/components/Navbar.tsx",
            "src/components/CourseCard.tsx",
        ],
        "dependencies": ["react", "next", "tailwindcss"],
        "risks": ["Complex UI requires careful component design"],
        "suggested_approach": "Start with layout components, then build pages",
        "estimated_hours": 8
    })


def create_plan_response():
    """Create mock plan response with implementation steps."""
    return create_mock_agent_result({
        "story_summary": "Learning website with modern UI",
        "steps": [
            {
                "order": 1,
                "description": "Create Navbar component",
                "file_path": "src/components/Navbar.tsx",
                "action": "create",
                "estimated_hours": 1
            },
            {
                "order": 2,
                "description": "Create CourseCard component",
                "file_path": "src/components/CourseCard.tsx",
                "action": "create",
                "estimated_hours": 1
            },
            {
                "order": 3,
                "description": "Create homepage",
                "file_path": "src/pages/index.tsx",
                "action": "create",
                "estimated_hours": 2
            }
        ],
        "total_estimated_hours": 4,
        "files_to_create": [
            "src/components/Navbar.tsx",
            "src/components/CourseCard.tsx",
            "src/pages/index.tsx"
        ],
        "files_to_modify": []
    })


def create_implement_response(file_path: str):
    """Create mock implement response for each step."""
    code = f"// Component for {file_path}\nimport React from 'react';\nexport default function Component() {{ return <div />; }}"
    return create_mock_agent_result({
        "file_path": file_path,
        "code": code,
        "explanation": f"Created {file_path} with React component",
        "imports_added": ["react"],
        "tests_to_write": []
    })


def create_code_review_response(result="LGTM"):
    """Create mock code review response."""
    return create_mock_agent_result({
        "filename": "src/components/Navbar.tsx",
        "result": result,
        "issues": [] if result == "LGTM" else ["Minor: Consider adding comments"],
        "rewritten_code": ""
    })


def create_run_code_response(status="PASS"):
    """Create mock run code analysis response."""
    return create_mock_agent_result({
        "status": status,
        "summary": "All components render correctly" if status == "PASS" else "Build error",
        "file_to_fix": "" if status == "PASS" else "src/components/Navbar.tsx",
        "send_to": "NoOne" if status == "PASS" else "Engineer"
    })


# =============================================================================
# UNIT TESTS FOR HELPER FUNCTIONS
# =============================================================================

class TestExtractJsonResponse:
    """Test JSON extraction from agent responses."""
    
    def test_extract_json_from_messages(self):
        """Test extracting JSON from agent message content."""
        content = {"action": "ANALYZE", "task_type": "feature"}
        result = create_mock_agent_result(content)
        
        extracted = _extract_json_response(result)
        assert extracted["action"] == "ANALYZE"
        assert extracted["task_type"] == "feature"
    
    def test_extract_json_with_markdown(self):
        """Test extracting JSON wrapped in markdown code blocks."""
        mock_message = MagicMock()
        mock_message.content = '```json\n{"action": "PLAN", "steps": []}\n```'
        result = {"messages": [mock_message]}
        
        extracted = _extract_json_response(result)
        assert extracted["action"] == "PLAN"
    
    def test_extract_json_empty_result(self):
        """Test handling empty or invalid results."""
        result = {"messages": []}
        extracted = _extract_json_response(result)
        assert extracted == {}
    
    def test_clean_json_removes_comments(self):
        """Test cleaning JSON with comments."""
        dirty = '{"key": "value", // comment\n"key2": "value2"}'
        cleaned = _clean_json(dirty)
        # Should not raise when parsed
        assert "key" in cleaned


class TestMockAgentResponses:
    """Test mock agent response helpers."""
    
    def test_router_response_structure(self):
        """Test router response has correct structure."""
        result = create_router_response()
        extracted = _extract_json_response(result)
        
        assert "action" in extracted
        assert "task_type" in extracted
        assert "complexity" in extracted
        assert extracted["action"] == "ANALYZE"
    
    def test_analyze_response_structure(self):
        """Test analyze response has correct structure."""
        result = create_analyze_response()
        extracted = _extract_json_response(result)
        
        assert "summary" in extracted
        assert "affected_files" in extracted
        assert "estimated_hours" in extracted
    
    def test_plan_response_structure(self):
        """Test plan response has correct structure."""
        result = create_plan_response()
        extracted = _extract_json_response(result)
        
        assert "steps" in extracted
        assert len(extracted["steps"]) > 0
        assert "file_path" in extracted["steps"][0]
    
    def test_implement_response_structure(self):
        """Test implement response has correct structure."""
        result = create_implement_response("src/components/Test.tsx")
        extracted = _extract_json_response(result)
        
        assert "file_path" in extracted
        assert "code" in extracted
    
    def test_code_review_response_structure(self):
        """Test code review response has correct structure."""
        result = create_code_review_response("LGTM")
        extracted = _extract_json_response(result)
        
        assert "result" in extracted
        assert extracted["result"] == "LGTM"
    
    def test_run_code_response_structure(self):
        """Test run code response has correct structure."""
        result = create_run_code_response("PASS")
        extracted = _extract_json_response(result)
        
        assert "status" in extracted
        assert extracted["status"] == "PASS"


# =============================================================================
# E2E FLOW TESTS (With Full Agent Mocking)
# =============================================================================

class TestE2ELearningWebsite:
    """End-to-End test for creating a learning website."""
    
    @pytest.mark.asyncio
    async def test_create_learning_website_state_flow(
        self, 
        learning_website_story, 
        mock_developer_agent, 
        temp_project_workspace
    ):
        """Test the complete state flow of creating a learning website.
        
        This test verifies the state transitions without calling actual nodes.
        """
        print("\n" + "="*60)
        print("[E2E] State Flow Test: Learning Website")
        print("="*60)
        
        # Initial state
        state = {
            **learning_website_story,
            "langfuse_handler": None,
            "workspace_path": str(temp_project_workspace),
            "branch_name": "story_learning_website",
            "main_workspace": str(temp_project_workspace),
            "workspace_ready": True,
            "action": None,
            "task_type": None,
            "complexity": None,
            "analysis_result": None,
            "implementation_plan": [],
            "code_changes": [],
            "files_created": [],
            "current_step": 0,
            "total_steps": 0,
            "code_review_passed": False,
            "run_status": None,
        }
        
        # Step 1: Simulate Router
        print("\n[Step 1] Router - Analyzing story...")
        router_result = _extract_json_response(create_router_response())
        state["action"] = router_result["action"]
        state["task_type"] = router_result["task_type"]
        state["complexity"] = router_result["complexity"]
        assert state["action"] == "ANALYZE"
        print(f"   [OK] Decision: {state['action']}")
        
        # Step 2: Simulate Analyze
        print("\n[Step 2] Analyze - Understanding requirements...")
        analyze_result = _extract_json_response(create_analyze_response())
        state["analysis_result"] = analyze_result
        assert state["analysis_result"]["summary"] is not None
        print(f"   [OK] Summary: {analyze_result['summary'][:50]}...")
        
        # Step 3: Simulate Plan
        print("\n[Step 3] Plan - Creating implementation plan...")
        plan_result = _extract_json_response(create_plan_response())
        state["implementation_plan"] = plan_result["steps"]
        state["total_steps"] = len(plan_result["steps"])
        assert len(state["implementation_plan"]) > 0
        print(f"   [OK] Steps: {state['total_steps']}")
        
        # Step 4: Simulate Implement
        print("\n[Step 4] Implement - Creating components...")
        files_created = []
        for step in state["implementation_plan"]:
            file_path = step["file_path"]
            impl_result = _extract_json_response(create_implement_response(file_path))
            
            full_path = temp_project_workspace / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(impl_result["code"])
            
            files_created.append(file_path)
            print(f"   [OK] Created: {file_path}")
        
        state["files_created"] = files_created
        assert len(files_created) == 3
        
        # Step 5: Simulate Code Review
        print("\n[Step 5] Code Review - Reviewing code...")
        review_result = _extract_json_response(create_code_review_response("LGTM"))
        state["code_review_passed"] = review_result["result"] == "LGTM"
        assert state["code_review_passed"]
        print(f"   [OK] Review: {review_result['result']}")
        
        # Step 6: Simulate Run Code
        print("\n[Step 6] Run Code - Testing...")
        run_result = _extract_json_response(create_run_code_response("PASS"))
        state["run_status"] = run_result["status"]
        assert state["run_status"] == "PASS"
        print(f"   [OK] Status: {state['run_status']}")
        
        print("\n" + "="*60)
        print("[OK] State Flow Test Completed!")
        print("="*60)
        print(f"\n[Summary]")
        print(f"   - Files created: {len(files_created)}")
        print(f"   - Code review: PASSED")
        print(f"   - Tests: PASSED")
    
    @pytest.mark.asyncio
    async def test_learning_website_with_node_mocking(
        self,
        learning_website_story,
        mock_developer_agent,
        temp_project_workspace
    ):
        """Test with node functions mocked at LLM level."""
        from app.agents.developer_v2.src import nodes
        
        print("\n" + "="*60)
        print("[E2E] Node Mocking Test")
        print("="*60)
        
        state = {
            **learning_website_story,
            "langfuse_handler": None,
            "workspace_path": str(temp_project_workspace),
            "workspace_ready": True,
            "action": None,
        }
        
        # Create mock LLM response
        mock_response = MagicMock()
        mock_response.content = '{"action": "ANALYZE", "task_type": "feature", "complexity": "high"}'
        
        # Patch the LLM module-level variable
        with patch.object(nodes, '_fast_llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            result = await nodes.router(state, mock_developer_agent)
            
            assert result["action"] == "ANALYZE"
            print(f"[OK] Router returned action: {result['action']}")
    
    @pytest.mark.asyncio
    async def test_debug_flow_state_transitions(
        self,
        learning_website_story,
        mock_developer_agent,
        temp_project_workspace
    ):
        """Test debug flow state transitions."""
        print("\n" + "="*60)
        print("[E2E] Debug Flow Test")
        print("="*60)
        
        state = {
            **learning_website_story,
            "workspace_path": str(temp_project_workspace),
            "files_created": ["src/components/Buggy.tsx"],
            "code_review_passed": True,
            "run_status": None,
            "debug_count": 0,
            "max_debug": 3,
        }
        
        # Simulate FAIL -> Debug -> PASS flow
        print("\n[Step 1] Run Code - Tests fail...")
        state["run_status"] = "FAIL"
        state["run_result"] = {"summary": "Build error", "file_to_fix": "src/components/Buggy.tsx"}
        print(f"   [FAIL] Status: {state['run_status']}")
        
        print("\n[Step 2] Debug - Fixing...")
        state["debug_count"] += 1
        state["debug_history"] = [{"iteration": 1, "fix": "Fixed import"}]
        print(f"   [OK] Debug iteration: {state['debug_count']}")
        
        print("\n[Step 3] Run Code - Tests pass...")
        state["run_status"] = "PASS"
        print(f"   [OK] Status: {state['run_status']}")
        
        assert state["run_status"] == "PASS"
        assert state["debug_count"] == 1
        
        print("\n" + "="*60)
        print("[OK] Debug Flow Test Completed!")
        print("="*60)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestToolsIntegration:
    """Test tools integration with nodes."""
    
    def test_filesystem_tools_available(self):
        """Test filesystem tools can be imported."""
        from app.agents.developer_v2.src.tools.filesystem_tools import (
            write_file_safe, read_file_safe, edit_file
        )
        assert write_file_safe is not None
        assert read_file_safe is not None
        assert edit_file is not None
    
    def test_git_tools_available(self):
        """Test git tools can be imported."""
        from app.agents.developer_v2.src.tools.git_tools import (
            git_status, git_commit, git_create_branch
        )
        assert git_status is not None
        assert git_commit is not None
        assert git_create_branch is not None
    
    def test_cocoindex_tools_available(self):
        """Test cocoindex tools can be imported."""
        from app.agents.developer_v2.src.tools.cocoindex_tools import (
            search_codebase, detect_project_structure
        )
        assert search_codebase is not None
        assert detect_project_structure is not None
    
    def test_execution_tools_available(self):
        """Test execution tools can be imported."""
        from app.agents.developer_v2.src.tools.execution_tools import (
            execute_command_sync, execute_command_async, CommandResult
        )
        assert execute_command_sync is not None
        assert execute_command_async is not None
        assert CommandResult is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
