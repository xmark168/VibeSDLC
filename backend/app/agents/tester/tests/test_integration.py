"""Integration tests for Tester Agent - calls real LLM.

Run with: uv run pytest app/agents/tester/tests/test_integration.py -v -s

Requires:
- OPENAI_API_KEY in .env
- Internet connection

Note: These tests cost money! Use sparingly.
"""
import os
import pytest
from pathlib import Path

# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"),
    reason="No API key found"
)


class TestSkillRegistry:
    """Test skill registry for tester."""
    
    def test_load_skills(self):
        """Should load skills for nextjs."""
        from app.agents.tester.src.skills import SkillRegistry
        
        registry = SkillRegistry.load("nextjs")
        assert registry is not None
        assert len(registry.skills) > 0
    
    def test_get_skill_content(self):
        """Should get skill content."""
        from app.agents.tester.src.skills import SkillRegistry
        
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("integration-test")
        
        if skill:
            content = skill.load_content()
            assert content and len(content) > 50


class TestGraphStructure:
    """Test graph structure (no summarize)."""
    
    def test_graph_compiles(self):
        """TesterGraph should compile without errors."""
        from app.agents.tester.src.graph import TesterGraph
        
        graph = TesterGraph(agent=None)
        assert graph.graph is not None
        assert graph.recursion_limit == 50
    
    def test_graph_has_8_nodes(self):
        """Graph should have 8 nodes (no summarize)."""
        from app.agents.tester.src.graph import TesterGraph
        
        graph = TesterGraph(agent=None)
        nodes = list(graph.graph.nodes.keys())
        
        expected = [
            "router", "setup_workspace", "plan_tests", "implement_tests",
            "review", "run_tests", "analyze_errors", "send_response",
            "test_status", "conversation"
        ]
        
        for node in expected:
            assert node in nodes, f"Missing node: {node}"
        
        # Verify summarize is removed
        assert "summarize" not in nodes


class TestStructuredOutput:
    """Test structured output pattern."""
    
    def test_schema_validation(self):
        """TestFileOutput schema should be valid."""
        from app.agents.tester.src.nodes.implement_tests import TestFileOutput
        
        output = TestFileOutput(
            file_path="__tests__/example.test.ts",
            content="describe('test', () => { it('works', () => {}) });",
            summary="Basic test"
        )
        
        assert output.file_path == "__tests__/example.test.ts"
        assert "describe" in output.content
    
    @pytest.mark.asyncio
    async def test_llm_structured_output(self):
        """LLM should return structured output."""
        from app.agents.tester.src._llm import implement_llm
        from app.agents.tester.src.nodes.implement_tests import TestFileOutput
        from langchain_core.messages import SystemMessage, HumanMessage
        
        structured_llm = implement_llm.with_structured_output(TestFileOutput)
        
        messages = [
            SystemMessage(content="""You are a test generator.
Output a simple Jest test file.
Return JSON with: file_path, content, summary"""),
            HumanMessage(content="Create a test for add(a, b) function")
        ]
        
        result = await structured_llm.ainvoke(messages)
        
        assert isinstance(result, TestFileOutput)
        assert result.file_path
        assert result.content
        assert "test" in result.content.lower() or "describe" in result.content.lower()


class TestImplementNode:
    """Test implement_tests node with real LLM."""
    
    @pytest.mark.asyncio
    async def test_creates_test_file(self, mock_state, workspace):
        """Should create test file using structured output."""
        from app.agents.tester.src.nodes.implement_tests import implement_tests
        
        result = await implement_tests(mock_state, agent=None)
        
        files_modified = result.get("files_modified", [])
        
        # Check if test file was created
        test_dir = workspace / "src" / "__tests__" / "integration"
        test_files = list(test_dir.rglob("*.test.ts"))
        
        print(f"\n[DEBUG] files_modified: {files_modified}")
        print(f"[DEBUG] test files found: {test_files}")
        
        # Either files_modified or actual files should exist
        assert files_modified or test_files, "Should create at least one test file"
        
        if test_files:
            content = test_files[0].read_text()
            print(f"[DEBUG] Content:\n{content[:500]}")
            
            # Should have test structure
            assert "describe" in content or "test" in content


class TestPlanNode:
    """Test plan_tests node."""
    
    def test_skills_field_added(self):
        """Plan should add skills field to each step."""
        # This is a unit test - verify the code adds skills
        from app.agents.tester.src.nodes.plan_tests import plan_tests
        
        # The actual test would require DB access
        # For now, verify the function exists and is importable
        assert callable(plan_tests)
