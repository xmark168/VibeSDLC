#!/usr/bin/env python
"""Standalone test runner for Tester Agent.

Run: uv run python app/agents/tester/tests/run_tests.py

Tests:
1. Skill registry loading
2. Graph initialization
3. Prompts loading
4. Plan tests node
5. Implement tests node (structured output)
"""
import asyncio
import sys
import json
from pathlib import Path
from uuid import uuid4

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Load .env
from dotenv import load_dotenv
load_dotenv(backend_path / ".env")


def test_skill_registry():
    """Test SkillRegistry loading for tester."""
    print("\n=== Test Skill Registry ===")
    
    from app.agents.tester.src.skills import SkillRegistry
    
    registry = SkillRegistry.load("nextjs")
    assert registry is not None, "Should load registry"
    assert len(registry.skills) > 0, "Should have skills"
    print(f"[PASS] Loaded {len(registry.skills)} skills for nextjs")
    print(f"       Skills: {list(registry.skills.keys())}")
    
    # Test get skill
    skill = registry.get_skill("integration-test")
    if skill:
        print(f"[PASS] Found skill: {skill.id}")
        content = skill.load_content()
        assert content and len(content) > 100, "Should have content"
        print(f"[PASS] Skill content: {len(content)} chars")
    else:
        print("[SKIP] integration-test skill not found")


def test_graph_initialization():
    """Test TesterGraph can be initialized."""
    print("\n=== Test Graph Initialization ===")
    
    from app.agents.tester.src.graph import TesterGraph
    
    tester_graph = TesterGraph(agent=None)
    
    assert tester_graph.graph is not None, "Should compile graph"
    print("[PASS] TesterGraph compiled successfully")
    
    # Check nodes exist (8 nodes, no summarize)
    expected_nodes = [
        "router", "setup_workspace", "plan_tests", "implement_tests",
        "review", "run_tests", "analyze_errors", "send_response"
    ]
    
    graph_nodes = list(tester_graph.graph.nodes.keys())
    print(f"[INFO] Graph nodes: {graph_nodes}")
    
    for node in expected_nodes:
        assert node in graph_nodes, f"Missing node: {node}"
    
    # Verify summarize is NOT in graph
    assert "summarize" not in graph_nodes, "summarize should be removed"
    
    print(f"[PASS] All {len(expected_nodes)} nodes present (no summarize)")


def test_prompts_loading():
    """Test prompts YAML loading."""
    print("\n=== Test Prompts Loading ===")
    
    from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
    
    # Test plan prompt (renamed from plan_tests)
    plan_system = get_system_prompt("plan_tests")
    assert plan_system and len(plan_system) > 100, "Should have plan system prompt"
    print(f"[PASS] plan_tests system prompt: {len(plan_system)} chars")
    
    # Test implement prompt
    impl_system = get_system_prompt("implement")
    assert impl_system and len(impl_system) > 100, "Should have implement system prompt"
    print(f"[PASS] implement system prompt: {len(impl_system)} chars")
    
    # Test review prompt
    review_system = get_system_prompt("review")
    assert review_system and len(review_system) > 100, "Should have review system prompt"
    print(f"[PASS] review system prompt: {len(review_system)} chars")
    
    # Test analyze_error prompt
    error_system = get_system_prompt("analyze_error")
    assert error_system and len(error_system) > 100, "Should have analyze_error system prompt"
    print(f"[PASS] analyze_error system prompt: {len(error_system)} chars")


def test_structured_output_schema():
    """Test TestFileOutput schema."""
    print("\n=== Test Structured Output Schema ===")
    
    from app.agents.tester.src.nodes.implement_tests import TestFileOutput
    
    # Test valid output
    output = TestFileOutput(
        file_path="__tests__/example.test.ts",
        content="describe('test', () => { it('works', () => {}) });",
        summary="Basic test"
    )
    
    assert output.file_path == "__tests__/example.test.ts"
    assert "describe" in output.content
    print("[PASS] TestFileOutput schema works")


def test_llm_configuration():
    """Test LLM can be configured."""
    print("\n=== Test LLM Configuration ===")
    
    import os
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("[SKIP] No API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
        return False
    
    from app.agents.tester.src._llm import plan_llm, implement_llm, review_llm
    
    assert plan_llm is not None, "Should have plan LLM"
    assert implement_llm is not None, "Should have implement LLM"
    assert review_llm is not None, "Should have review LLM"
    
    print("[PASS] All LLMs configured")
    return True


async def test_implement_structured_output():
    """Test implement_tests with structured output."""
    print("\n=== Test Implement Structured Output (LLM) ===")
    
    import os
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        print("[SKIP] No API key")
        return
    
    from app.agents.tester.src._llm import implement_llm
    from app.agents.tester.src.nodes.implement_tests import TestFileOutput
    from langchain_core.messages import SystemMessage, HumanMessage
    
    structured_llm = implement_llm.with_structured_output(TestFileOutput)
    
    messages = [
        SystemMessage(content="""You are a test generator.
Output a simple Jest test file for a math utility.
Return JSON with: file_path, content, summary"""),
        HumanMessage(content="Create a test for add(a, b) function that returns a + b")
    ]
    
    print("[INFO] Calling LLM with structured output...")
    result = await structured_llm.ainvoke(messages)
    
    assert isinstance(result, TestFileOutput), "Should return TestFileOutput"
    assert result.file_path, "Should have file_path"
    assert result.content, "Should have content"
    assert "test" in result.content.lower() or "describe" in result.content.lower()
    
    print(f"[PASS] Structured output works!")
    print(f"  file_path: {result.file_path}")
    print(f"  content: {result.content[:200]}...")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Tester Agent Tests")
    print("=" * 60)
    
    try:
        # Sync tests
        test_skill_registry()
        test_graph_initialization()
        test_prompts_loading()
        test_structured_output_schema()
        has_api_key = test_llm_configuration()
        
        # Async tests (require API key)
        if has_api_key:
            print("\n" + "=" * 60)
            print("LLM Integration Tests")
            print("=" * 60)
            
            loop = asyncio.get_event_loop()
            loop.run_until_complete(test_implement_structured_output())
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
