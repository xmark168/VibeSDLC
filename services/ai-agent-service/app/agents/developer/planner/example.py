#!/usr/bin/env python3
"""
Example usage of the DeepAgents Planner

This demonstrates how simple the DeepAgents version is compared to LangGraph.
"""

import asyncio
import os
from app.agents.developer.planner_deepagents import run_planner, create_planner_agent


async def example_1_basic():
    """Example 1: Basic usage - super simple!"""
    print("=" * 80)
    print("Example 1: Basic Usage (DeepAgents)")
    print("=" * 80)

    result = await run_planner(
        user_request="Add user authentication with JWT tokens to the FastAPI app",
        working_directory="./src"
    )

    print(f"\n📋 Plan: {result.get('proposed_plan_title', 'Implementation Plan')}")
    print(f"\n📝 Steps ({len(result.get('proposed_plan', []))} total):")
    for i, step in enumerate(result.get('proposed_plan', [])[:5], 1):
        print(f"{i}. {step}")

    if len(result.get('proposed_plan', [])) > 5:
        print(f"... and {len(result.get('proposed_plan', [])) - 5} more")

    print(f"\n📊 Actions taken: {result.get('action_count', 0)}")
    print(f"\n📄 Context notes: {len(result.get('context_gathering_notes', ''))} characters")


async def example_2_with_rules():
    """Example 2: With custom rules"""
    print("\n" + "=" * 80)
    print("Example 2: With Custom Rules")
    print("=" * 80)

    result = await run_planner(
        user_request="Implement payment processing with Stripe",
        working_directory="./src",
        custom_rules={
            "general_rules": """
- Follow PEP 8 strictly
- Use type hints for all functions
- Write docstrings (Google style)
            """,
            "testing_instructions": """
- Use pytest
- Minimum 80% coverage
- Test all edge cases
            """,
            "dependencies_and_installation": """
- Python 3.13+
- FastAPI framework
- SQLModel for ORM
            """
        }
    )

    print(f"\n✅ Generated plan with {len(result.get('proposed_plan', []))} steps")
    print(f"📝 First 3 steps:")
    for i, step in enumerate(result.get('proposed_plan', [])[:3], 1):
        print(f"   {i}. {step}")


async def example_3_advanced():
    """Example 3: Advanced - create agent first"""
    print("\n" + "=" * 80)
    print("Example 3: Advanced Usage")
    print("=" * 80)

    # Create the agent
    agent = create_planner_agent(
        working_directory="./src",
        codebase_tree="""
src/
  api/
    routes/
    models/
  auth/
  services/
  utils/
tests/
  unit/
  integration/
        """,
        model_name="gpt-4"
    )

    # Create initial state
    initial_state = {
        "messages": [{"role": "user", "content": "Add WebSocket support for real-time updates"}],
        "user_request": "Add WebSocket support for real-time updates",
        "working_directory": "./src",
    }

    # Run the agent
    result = await agent.ainvoke(initial_state)

    print(f"\n✅ Plan generated!")
    print(f"📊 Total steps: {len(result.get('proposed_plan', []))}")


async def example_4_comparison():
    """Example 4: Show how simple DeepAgents is"""
    print("\n" + "=" * 80)
    print("Example 4: Simplicity Comparison")
    print("=" * 80)

    print("""
With LangGraph (complex):
    1. Define state schema
    2. Create nodes (7+ functions)
    3. Build graph with edges
    4. Add conditional routing (5+ functions)
    5. Compile graph
    6. Invoke with config
    → ~1500 lines of code

With DeepAgents (simple):
    result = await run_planner("Add feature X")
    → ~600 lines of code

That's a 60% reduction in complexity!
    """)


async def main():
    """Run all examples"""
    print("\n" + "🤖" * 40)
    print("DeepAgents Planner - Usage Examples")
    print("🤖" * 40)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("\n❌ Error: Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return

    try:
        await example_1_basic()
        await example_2_with_rules()
        await example_3_advanced()
        await example_4_comparison()

        print("\n" + "=" * 80)
        print("✅ All examples completed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
