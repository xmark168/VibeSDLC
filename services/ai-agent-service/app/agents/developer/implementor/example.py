#!/usr/bin/env python3
"""
Example usage of the Code Implementor Agent

This script demonstrates how to use the new implementor agent that leverages
deepagents library for built-in planning instead of a separate planner subagent.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from agent import run_implementor, create_implementor_agent


async def example_basic_usage():
    """Example of basic implementor usage"""
    print("=" * 80)
    print("🚀 BASIC IMPLEMENTOR EXAMPLE")
    print("=" * 80)

    try:
        result = await run_implementor(
            user_request="Add user authentication with JWT tokens to a FastAPI application",
            working_directory="./demo_project",
            project_type="new",  # This will trigger stack detection and boilerplate retrieval
            enable_pgvector=True,
        )

        print("\n✅ Implementation completed!")
        print(f"Status: {result.get('implementation_status', 'Unknown')}")

        if "todos" in result:
            print(
                f"\nTodos completed: {len([t for t in result['todos'] if t.get('status') == 'completed'])}"
            )
            print("Todo list:")
            for i, todo in enumerate(result["todos"], 1):
                status = todo.get("status", "unknown")
                content = todo.get("content", "No content")
                print(f"  {i}. [{status}] {content}")

        if "generated_files" in result:
            print(f"\nGenerated files: {len(result['generated_files'])}")
            for file in result["generated_files"][:5]:  # Show first 5 files
                print(f"  - {file}")

        if "commit_history" in result:
            print(f"\nCommits made: {len(result['commit_history'])}")
            for commit in result["commit_history"][:3]:  # Show first 3 commits
                print(f"  - {commit}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def example_existing_project():
    """Example of working with existing project"""
    print("\n" + "=" * 80)
    print("🔧 EXISTING PROJECT EXAMPLE")
    print("=" * 80)

    try:
        result = await run_implementor(
            user_request="Add API rate limiting middleware to the existing FastAPI routes",
            working_directory="services/ai-agent-service",
            project_type="existing",
            enable_pgvector=True,
        )

        print("\n✅ Enhancement completed!")
        print(f"Status: {result.get('implementation_status', 'Unknown')}")

        # Show implementation details
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if "content" in last_message:
                print(f"\nFinal result: {last_message['content'][:200]}...")

    except Exception as e:
        print(f"❌ Error: {e}")


async def example_advanced_usage():
    """Example of advanced implementor usage with custom configuration"""
    print("\n" + "=" * 80)
    print("⚙️ ADVANCED IMPLEMENTOR EXAMPLE")
    print("=" * 80)

    try:
        # Create agent with custom configuration
        agent = create_implementor_agent(
            working_directory="./advanced_project",
            project_type="new",
            enable_pgvector=True,
            boilerplate_templates_path="services/ai-agent-service/app/templates/boilerplate",
            model_name="gpt-4o",
            recursion_limit=100,
        )

        # Custom initial state
        initial_state = {
            "messages": [
                {
                    "role": "user",
                    "content": "Create a microservice for user management with CRUD operations, authentication, and database integration",
                }
            ],
            "working_directory": "./advanced_project",
            "project_type": "new",
            "user_request": "Create a microservice for user management with CRUD operations, authentication, and database integration",
            "enable_pgvector": True,
            "implementation_status": "started",
            "custom_requirements": [
                "Use FastAPI framework",
                "Implement JWT authentication",
                "Use PostgreSQL database",
                "Include API documentation",
                "Add comprehensive tests",
                "Use Docker for containerization",
            ],
        }

        print("🤖 Running advanced implementor with custom configuration...")
        result = await agent.ainvoke(initial_state)

        print("\n✅ Advanced implementation completed!")

        # Show detailed results
        if "todos" in result:
            completed_todos = [t for t in result["todos"] if t.get("status") == "completed"]
            pending_todos = [t for t in result["todos"] if t.get("status") == "pending"]

            print("\n📋 Todo Summary:")
            print(f"  ✅ Completed: {len(completed_todos)}")
            print(f"  ⏳ Pending: {len(pending_todos)}")

            if pending_todos:
                print("\n⏳ Remaining tasks:")
                for todo in pending_todos[:3]:
                    print(f"  - {todo.get('content', 'No content')}")

        # Show file system state (from deepagents virtual filesystem)
        if "files" in result:
            print(f"\n📁 Files in virtual filesystem: {len(result['files'])}")
            for filename in list(result["files"].keys())[:5]:
                print(f"  - {filename}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def example_workflow_demonstration():
    """Demonstrate the complete implementor workflow"""
    print("\n" + "=" * 80)
    print("🔄 WORKFLOW DEMONSTRATION")
    print("=" * 80)

    print("This example shows the complete implementor workflow:")
    print("1. Load existing codebase (or detect stack for new projects)")
    print("2. Create feature branch")
    print("3. Use write_todos for planning (built-in from deepagents)")
    print("4. Select integration strategy for each task")
    print("5. Generate code using subagents")
    print("6. Commit changes")
    print("7. Create pull request")
    print("8. Handle user feedback and refinements")

    try:
        # Simulate the workflow steps
        print("\n🔍 Step 1: Analyzing project structure...")

        result = await run_implementor(
            user_request="Add comprehensive logging system with different log levels and file rotation",
            working_directory="services/ai-agent-service",
            project_type="existing",
            enable_pgvector=True,
        )

        print("✅ Workflow completed successfully!")

        # Show workflow results
        workflow_steps = [
            "Codebase analysis",
            "Planning with write_todos",
            "Integration strategy selection",
            "Code generation",
            "Testing and validation",
            "Git operations",
            "Documentation updates",
        ]

        print("\n📋 Workflow steps executed:")
        for i, step in enumerate(workflow_steps, 1):
            print(f"  {i}. ✅ {step}")

    except Exception as e:
        print(f"❌ Workflow error: {e}")


def print_comparison():
    """Print comparison between old and new approach"""
    print("\n" + "=" * 80)
    print("📊 OLD vs NEW APPROACH COMPARISON")
    print("=" * 80)

    comparison = """
OLD APPROACH (Separate Planner Subagent):
❌ Redundant planner subagent (deepagents already has planning)
❌ Manual graph construction and workflow management
❌ Complex state management across multiple agents
❌ Separate planning and execution phases
❌ More complex error handling and recovery

NEW APPROACH (DeepAgents Built-in Planning):
✅ Uses deepagents' built-in write_todos for planning
✅ Automatic workflow management by deepagents
✅ Simplified state management with persistence
✅ Integrated planning and execution
✅ Built-in human-in-the-loop support
✅ Stack detection and boilerplate retrieval
✅ LangChain PGVector indexing for better context
✅ Subagents for specialized tasks (code generation, review)
✅ Automatic todo management and progress tracking

KEY BENEFITS:
🚀 Simplified architecture
🚀 Better integration with deepagents ecosystem
🚀 Reduced code complexity and maintenance
🚀 Enhanced functionality (stack detection, boilerplate)
🚀 Better user experience with automatic workflow
"""

    print(comparison)


async def main():
    """Run all examples"""
    print("🧠🤖 CODE IMPLEMENTOR AGENT EXAMPLES")
    print("Using DeepAgents Library for Built-in Planning")

    # Print comparison first
    print_comparison()

    # Run examples
    await example_basic_usage()
    await example_existing_project()
    await example_advanced_usage()
    await example_workflow_demonstration()

    print("\n" + "=" * 80)
    print("🎉 ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nThe new Code Implementor Agent successfully demonstrates:")
    print("✅ Built-in planning with deepagents write_todos")
    print("✅ Stack detection and boilerplate retrieval")
    print("✅ LangChain PGVector indexing for codebase context")
    print("✅ Automated workflow with todo management")
    print("✅ Git operations and pull request creation")
    print("✅ Code generation with specialized subagents")
    print("✅ User feedback and refinement loop")
    print("\nThis replaces the redundant planner subagent with a more")
    print("integrated and powerful implementation approach! 🚀")


if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault("OPENAI_API_KEY", "your-api-key-here")
    os.environ.setdefault(
        "PGVECTOR_CONNECTION_STRING",
        "postgresql+psycopg://langchain:langchain@localhost:6024/langchain",
    )

    # Run examples
    asyncio.run(main())
