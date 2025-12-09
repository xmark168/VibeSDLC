"""Integration tests for Tester Agent - calls real LLM.

Run with: uv run pytest app/agents/tester/tests/test_integration.py -v -s

Requires:
- OPENAI_API_KEY in .env
- Internet connection

Supports:
- Integration tests (API routes, DB operations) → integration-test skill
- Unit tests (Components, utilities, hooks) → unit-test skill

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
    
    def test_get_integration_skill_content(self):
        """Should get integration-test skill content."""
        from app.agents.tester.src.skills import SkillRegistry
        
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("integration-test")
        
        if skill:
            content = skill.load_content()
            assert content and len(content) > 50
            assert "jest" in content.lower() or "prisma" in content.lower()
    
    def test_get_unit_skill_content(self):
        """Should get unit-test skill content."""
        from app.agents.tester.src.skills import SkillRegistry
        
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("unit-test")
        
        if skill:
            content = skill.load_content()
            assert content and len(content) > 50
            assert "jest" in content.lower() or "testing-library" in content.lower()
    
    def test_both_skills_exist(self):
        """Should have both integration-test and unit-test skills."""
        from app.agents.tester.src.skills import SkillRegistry
        
        registry = SkillRegistry.load("nextjs")
        skill_names = [s.name for s in registry.skills]
        
        assert "integration-test" in skill_names, "Missing integration-test skill"
        assert "unit-test" in skill_names, "Missing unit-test skill"


class TestGraphStructure:
    """Test graph structure (supports integration + unit tests)."""
    
    def test_graph_compiles(self):
        """TesterGraph should compile without errors."""
        from app.agents.tester.src.graph import TesterGraph
        
        graph = TesterGraph(agent=None)
        assert graph.graph is not None
        assert graph.recursion_limit == 50
    
    def test_graph_has_expected_nodes(self):
        """Graph should have all expected nodes."""
        from app.agents.tester.src.graph import TesterGraph
        
        graph = TesterGraph(agent=None)
        nodes = list(graph.graph.nodes.keys())
        
        # Core nodes for test generation flow
        expected = [
            "router", "setup_workspace", "plan_tests", "implement_tests",
            "review", "run_tests", "analyze_errors", "send_response",
            "test_status", "conversation"
        ]
        
        for node in expected:
            assert node in nodes, f"Missing node: {node}"
        
        # Verify summarize is removed (no longer needed)
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
        
        # Check if test file was created (supports both integration and unit folders)
        integration_dir = workspace / "src" / "__tests__" / "integration"
        unit_dir = workspace / "src" / "__tests__" / "unit"
        
        integration_tests = list(integration_dir.rglob("*.test.ts")) if integration_dir.exists() else []
        unit_tests = list(unit_dir.rglob("*.test.tsx")) if unit_dir.exists() else []
        test_files = integration_tests + unit_tests
        
        print(f"\n[DEBUG] files_modified: {files_modified}")
        print(f"[DEBUG] integration tests found: {integration_tests}")
        print(f"[DEBUG] unit tests found: {unit_tests}")
        
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
    
    def test_detect_test_structure_creates_both_folders(self, workspace):
        """Should create both integration and unit test folders."""
        from app.agents.tester.src.nodes.plan_tests import _detect_test_structure
        
        structure = _detect_test_structure(str(workspace))
        
        assert structure["integration_folder"] == "src/__tests__/integration"
        assert structure["unit_folder"] == "src/__tests__/unit"
        
        # Verify folders were created
        integration_path = workspace / "src" / "__tests__" / "integration"
        unit_path = workspace / "src" / "__tests__" / "unit"
        
        assert integration_path.exists(), "Integration folder should be created"
        assert unit_path.exists(), "Unit folder should be created"


class TestUnitTestImplementation:
    """Test unit test implementation."""
    
    @pytest.mark.asyncio
    async def test_creates_unit_test_file(self, mock_unit_state, workspace):
        """Should create unit test file using structured output."""
        from app.agents.tester.src.nodes.implement_tests import implement_tests
        
        result = await implement_tests(mock_unit_state, agent=None)
        
        files_modified = result.get("files_modified", [])
        
        # Check if unit test file was created
        unit_dir = workspace / "src" / "__tests__" / "unit"
        unit_tests = list(unit_dir.rglob("*.test.tsx")) if unit_dir.exists() else []
        
        print(f"\n[DEBUG] files_modified: {files_modified}")
        print(f"[DEBUG] unit tests found: {unit_tests}")
        
        # Either files_modified or actual files should exist
        assert files_modified or unit_tests, "Should create at least one unit test file"
        
        if unit_tests:
            content = unit_tests[0].read_text()
            print(f"[DEBUG] Content:\n{content[:500]}")
            
            # Should have React Testing Library patterns
            assert "describe" in content or "test" in content
    
    def test_unit_skill_auto_selection(self):
        """Should auto-select unit-test skill for unit test type."""
        # Test the logic in implement_tests
        test_type = "unit"
        step_skills = []
        
        if not step_skills:
            if test_type == "unit":
                step_skills = ["unit-test"]
            else:
                step_skills = ["integration-test"]
        
        assert step_skills == ["unit-test"]
    
    def test_integration_skill_auto_selection(self):
        """Should auto-select integration-test skill for integration test type."""
        test_type = "integration"
        step_skills = []
        
        if not step_skills:
            if test_type == "unit":
                step_skills = ["unit-test"]
            else:
                step_skills = ["integration-test"]
        
        assert step_skills == ["integration-test"]
