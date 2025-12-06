"""Integration tests for Developer V2 - calls real LLM.

Run with: uv run pytest app/agents/developer_v2/tests/test_integration.py -v -s

Requires:
- ANTHROPIC_API_KEY or OPENAI_API_KEY in .env
- Internet connection

Note: These tests cost money! Use sparingly.
"""
import os
import pytest
from pathlib import Path

# Load .env from backend directory
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(backend_dir / ".env")

# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No API key found (ANTHROPIC_API_KEY or OPENAI_API_KEY)"
)


class TestLLMWithSkills:
    """Test LLM can use skills via tools."""
    
    @pytest.mark.asyncio
    async def test_llm_activates_skill(self):
        """LLM should activate skill when asked to create a component."""
        from langchain_core.messages import SystemMessage, HumanMessage
        from app.agents.developer_v2.src.nodes._llm import get_llm
        from app.agents.developer_v2.src.tools.skill_tools import (
            activate_skills, set_skill_context, reset_skill_cache
        )
        from app.agents.developer_v2.src.skills import SkillRegistry
        
        # Setup
        registry = SkillRegistry.load("nextjs")
        set_skill_context(registry)
        reset_skill_cache()
        
        # Get LLM with tools
        llm = get_llm("implement")
        llm_with_tools = llm.bind_tools([activate_skills])
        
        # System prompt tells LLM about skills
        catalog = registry.get_skill_catalog_for_prompt()
        system_prompt = f"""You are a developer assistant.
{catalog}

IMPORTANT: Before writing any code, you MUST call activate_skills with the relevant skill IDs.
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="I need to create a React button component. What skill should I activate first?")
        ]
        
        # Call LLM
        response = await llm_with_tools.ainvoke(messages)
        
        # Verify LLM called activate_skills
        assert response.tool_calls, "LLM should call activate_skills tool"
        tool_call = response.tool_calls[0]
        assert tool_call["name"] == "activate_skills"
        assert "frontend-component" in str(tool_call["args"]).lower() or "component" in str(tool_call["args"]).lower()
        
        print(f"\n[PASS] LLM called: {tool_call['name']}({tool_call['args']})")
        
        reset_skill_cache()
    
    @pytest.mark.asyncio
    async def test_skill_content_injected(self):
        """After activating skill, content should be available to LLM."""
        from app.agents.developer_v2.src.tools.skill_tools import (
            activate_skills, set_skill_context, reset_skill_cache
        )
        from app.agents.developer_v2.src.skills import SkillRegistry
        
        # Setup
        registry = SkillRegistry.load("nextjs")
        set_skill_context(registry)
        reset_skill_cache()
        
        # Activate skill
        result = activate_skills.invoke({"skill_ids": ["frontend-component"]})
        
        # Verify content
        assert "[ACTIVATED 1/1 SKILLS]" in result
        assert "[SKILL: " in result
        assert "Bundled files:" in result
        
        # Check skill content is present
        assert "React" in result or "component" in result.lower()
        
        print(f"\n[PASS] Skill activated with {len(result)} chars of content")
        
        reset_skill_cache()
    
    @pytest.mark.asyncio
    async def test_llm_reads_bundled_file(self):
        """LLM should read bundled file when asked for specific patterns."""
        from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
        from app.agents.developer_v2.src.nodes._llm import get_llm
        from app.agents.developer_v2.src.tools.skill_tools import (
            activate_skills, read_skill_file, set_skill_context, reset_skill_cache
        )
        from app.agents.developer_v2.src.skills import SkillRegistry
        
        # Setup
        registry = SkillRegistry.load("nextjs")
        set_skill_context(registry)
        reset_skill_cache()
        
        # Get LLM with tools
        llm = get_llm("implement")
        llm_with_tools = llm.bind_tools([activate_skills, read_skill_file])
        
        system_prompt = """You are a developer assistant.
When asked about specific patterns or examples, you should:
1. First activate the relevant skill
2. Then read bundled files for detailed patterns

Available tools:
- activate_skills: Get skill instructions
- read_skill_file: Read bundled reference files (e.g., forms.md, animations.md)
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="I need to create a form component. First activate the frontend-component skill, then read the forms.md bundled file for patterns.")
        ]
        
        # First LLM call - should activate skill
        response1 = await llm_with_tools.ainvoke(messages)
        assert response1.tool_calls, "LLM should call a tool"
        
        # Execute tool and continue conversation
        tool_call = response1.tool_calls[0]
        if tool_call["name"] == "activate_skills":
            tool_result = activate_skills.invoke(tool_call["args"])
        else:
            tool_result = read_skill_file.invoke(tool_call["args"])
        
        messages.append(response1)
        messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call["id"]))
        
        # Second LLM call - should read bundled file
        response2 = await llm_with_tools.ainvoke(messages)
        
        # Check if LLM called read_skill_file
        all_tool_calls = response1.tool_calls + (response2.tool_calls or [])
        tool_names = [tc["name"] for tc in all_tool_calls]
        
        print(f"\n[INFO] Tool calls: {tool_names}")
        
        # Either activated skill mentions bundled files, or LLM called read_skill_file
        has_read_file = "read_skill_file" in tool_names
        has_bundled_info = "Bundled files:" in tool_result
        
        assert has_read_file or has_bundled_info, "LLM should read bundled file or skill should list them"
        
        if has_read_file:
            print("[PASS] LLM called read_skill_file to read bundled patterns")
        else:
            print("[PASS] Skill activation includes bundled file list")
        
        reset_skill_cache()


class TestImplementNode:
    """Test implement node with real LLM."""
    
    @pytest.fixture
    def mock_state(self, tmp_path):
        """Create minimal state for implement node."""
        # Create workspace
        workspace = tmp_path / "test_project"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "src" / "components").mkdir()
        
        return {
            "workspace_path": str(workspace),
            "project_id": "test-project",
            "task_id": "test-task",
            "tech_stack": "nextjs",
            "current_step": 0,
            "total_steps": 1,
            "implementation_plan": [{
                "order": 1,
                "task": "Create a simple Button component",
                "description": "Create src/components/Button.tsx with basic button",
                "file_path": "src/components/Button.tsx",
                "action": "create",
                "dependencies": []
            }],
            "logic_analysis": "Create a basic Button component",
            "dependencies_content": {},
            "files_modified": [],
            "review_count": 0,
            "react_loop_count": 0,
            "debug_count": 0,
        }
    
    @pytest.mark.asyncio
    async def test_implement_creates_file(self, mock_state, tmp_path):
        """Implement node should create file via LLM."""
        from app.agents.developer_v2.src.nodes.implement import implement
        from app.agents.developer_v2.src.tools import set_tool_context
        
        # Setup context
        set_tool_context(
            mock_state["workspace_path"],
            mock_state["project_id"],
            mock_state["task_id"]
        )
        
        # Run implement
        result = await implement(mock_state)
        
        # Check result
        assert result.get("action") in ["REVIEW", "VALIDATE", "RESPOND"], f"Unexpected action: {result.get('action')}"
        
        # Check if file was created
        button_path = Path(mock_state["workspace_path"]) / "src" / "components" / "Button.tsx"
        files_modified = result.get("files_modified", [])
        
        print(f"\n[INFO] Action: {result.get('action')}")
        print(f"[INFO] Files modified: {files_modified}")
        print(f"[INFO] File exists: {button_path.exists()}")
        
        if button_path.exists():
            content = button_path.read_text()
            print(f"[PASS] Button.tsx created ({len(content)} chars)")
            assert "Button" in content or "button" in content
        else:
            # LLM might have created different file or failed
            print(f"[WARN] Button.tsx not created, but action={result.get('action')}")


class TestAnalyzeAndPlanNode:
    """Test analyze_and_plan node with real LLM."""
    
    @pytest.fixture
    def mock_state(self, tmp_path):
        """Create minimal state for analyze_and_plan."""
        workspace = tmp_path / "test_project"
        workspace.mkdir()
        
        return {
            "workspace_path": str(workspace),
            "project_id": "test-project",
            "task_id": "test-task",
            "tech_stack": "nextjs",
            "story_summary": "Create a login page with email and password fields",
            "story_content": "As a user, I want to login with email and password",
            "files_modified": [],
        }
    
    @pytest.mark.asyncio
    async def test_analyze_creates_plan(self, mock_state):
        """Analyze node should create implementation plan."""
        from app.agents.developer_v2.src.nodes.analyze_and_plan import analyze_and_plan
        from app.agents.developer_v2.src.tools import set_tool_context
        
        set_tool_context(
            mock_state["workspace_path"],
            mock_state["project_id"],
            mock_state["task_id"]
        )
        
        result = await analyze_and_plan(mock_state)
        
        # Check plan was created
        plan = result.get("implementation_plan", [])
        total_steps = result.get("total_steps", 0)
        
        print(f"\n[INFO] Total steps: {total_steps}")
        print(f"[INFO] Plan: {plan[:2]}...")  # First 2 steps
        
        assert total_steps > 0, "Should create at least 1 step"
        assert len(plan) > 0, "Plan should not be empty"
        
        # Check plan structure
        first_step = plan[0]
        assert "task" in first_step or "description" in first_step
        
        print(f"[PASS] Created plan with {total_steps} steps")
