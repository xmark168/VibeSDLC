"""
Sprint Executor Example

Simple examples demonstrating how to use Sprint Task Executor.
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from agents.developer.agent import (
    filter_development_tasks,
    format_task_as_request,
    SprintTaskExecutor,
)


# ============================================================================
# Example 1: Preview Tasks
# ============================================================================


def example_1_preview_tasks():
    """Preview which tasks would be executed in a sprint."""
    print("=" * 80)
    print("Example 1: Preview Tasks")
    print("=" * 80)

    sprint_id = "sprint-1"

    # Get Development/Infrastructure tasks
    tasks = filter_development_tasks(sprint_id)

    print(f"\nFound {len(tasks)} Development/Infrastructure tasks in {sprint_id}:\n")

    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task['id']}: {task['title']}")
        print(f"   Type: {task.get('task_type', 'N/A')}")
        print(f"   Estimate: {task.get('estimate_value', 'N/A')} hours")

        if task.get("dependencies"):
            print(f"   Dependencies: {', '.join(task['dependencies'])}")

        print()


# ============================================================================
# Example 2: Format Task as Request
# ============================================================================


def example_2_format_task():
    """Show how a task is formatted as user_request for Developer Agent."""
    print("=" * 80)
    print("Example 2: Format Task as Request")
    print("=" * 80)

    sprint_id = "sprint-1"

    # Get first Development task
    tasks = filter_development_tasks(sprint_id)

    if not tasks:
        print("No tasks found")
        return

    task = tasks[0]

    print(f"\nOriginal Task: {task['id']}")
    print(f"Title: {task['title']}")
    print("\nFormatted as user_request:\n")
    print("-" * 80)

    # Format task
    user_request = format_task_as_request(task)
    print(user_request)

    print("-" * 80)


# ============================================================================
# Example 3: Execute Sprint (Basic)
# ============================================================================


async def example_3_execute_sprint_basic():
    """Execute all Development/Infrastructure tasks in a sprint."""
    print("=" * 80)
    print("Example 3: Execute Sprint (Basic)")
    print("=" * 80)

    sprint_id = "sprint-1"
    working_directory = "./demo_project"  # Change to your project path

    print("\n⚠️  WARNING: This will execute Developer Agent for all tasks!")
    print(f"Sprint: {sprint_id}")
    print(f"Working Directory: {working_directory}")
    print("\nPress Ctrl+C to cancel...\n")

    # Uncomment to actually execute
    # await asyncio.sleep(3)

    # result = await execute_sprint(
    #     sprint_id=sprint_id,
    #     working_directory=working_directory,
    # )

    # print(f"\n✅ Execution completed!")
    # print(f"Status: {result['status']}")
    # print(f"Tasks Succeeded: {result['tasks_succeeded']}")
    # print(f"Tasks Failed: {result['tasks_failed']}")
    # print(f"Duration: {result['duration_seconds']:.2f}s")

    print("(Execution commented out for safety)")


# ============================================================================
# Example 4: Execute Sprint (Advanced)
# ============================================================================


async def example_4_execute_sprint_advanced():
    """Execute sprint with custom configuration."""
    print("=" * 80)
    print("Example 4: Execute Sprint (Advanced)")
    print("=" * 80)

    # Create executor with custom config
    executor = SprintTaskExecutor(
        working_directory="./demo_project",
        model_name="gpt-4o",  # Use more powerful model
        enable_pgvector=True,
    )

    sprint_id = "sprint-1"

    print("\nConfiguration:")
    print(f"  Sprint: {sprint_id}")
    print(f"  Working Directory: {executor.working_directory}")
    print(f"  Model: {executor.model_name}")
    print(f"  PGVector: {executor.enable_pgvector}")

    # Preview tasks first
    print("\nLoading sprint data...")
    sprint_data = executor.load_sprint(sprint_id)
    backlog_items = executor.load_backlog()

    print(f"  Sprint Goal: {sprint_data['sprint_goal']}")
    print(f"  Assigned Items: {len(sprint_data['assigned_items'])}")

    # Filter tasks
    dev_tasks = executor.filter_development_tasks(sprint_data, backlog_items)
    print(f"  Development Tasks: {len(dev_tasks)}")

    # Resolve dependencies
    sorted_tasks = executor.resolve_dependencies(dev_tasks, backlog_items)

    print("\nExecution order:")
    for i, task in enumerate(sorted_tasks, 1):
        deps = task.get("dependencies", [])
        deps_str = f" (depends on: {', '.join(deps)})" if deps else ""
        print(f"  {i}. {task['id']}: {task['title']}{deps_str}")

    # Execute (commented out for safety)
    # result = await executor.execute_sprint(
    #     sprint_id=sprint_id,
    #     continue_on_error=False,  # Stop on first error
    # )

    print("\n(Execution commented out for safety)")


# ============================================================================
# Example 5: Execute Single Task
# ============================================================================


async def example_5_execute_single_task():
    """Execute a single task manually."""
    print("=" * 80)
    print("Example 5: Execute Single Task")
    print("=" * 80)

    executor = SprintTaskExecutor(
        working_directory="./demo_project",
        model_name="gpt-4o-mini",
    )

    sprint_id = "sprint-1"

    # Get tasks
    sprint_data = executor.load_sprint(sprint_id)
    backlog_items = executor.load_backlog()
    dev_tasks = executor.filter_development_tasks(sprint_data, backlog_items)

    if not dev_tasks:
        print("No tasks found")
        return

    # Select first task
    task = dev_tasks[0]

    print("\nSelected Task:")
    print(f"  ID: {task['id']}")
    print(f"  Title: {task['title']}")
    print(f"  Type: {task.get('task_type', 'N/A')}")

    # Execute (commented out for safety)
    # result = await executor.execute_task(
    #     task=task,
    #     sprint_id=sprint_id,
    #     task_index=1,
    #     total_tasks=1,
    # )

    # if result["status"] == "success":
    #     print(f"\n✅ Task completed successfully!")
    #     dev_result = result["result"]
    #     print(f"Generated Files: {len(dev_result.get('generated_files', []))}")
    #     print(f"Commits: {len(dev_result.get('commit_history', []))}")
    # else:
    #     print(f"\n❌ Task failed: {result.get('error')}")

    print("\n(Execution commented out for safety)")


# ============================================================================
# Example 6: Custom Task Filtering
# ============================================================================


def example_6_custom_filtering():
    """Filter tasks with custom criteria."""
    print("=" * 80)
    print("Example 6: Custom Task Filtering")
    print("=" * 80)

    executor = SprintTaskExecutor()

    sprint_id = "sprint-1"
    sprint_data = executor.load_sprint(sprint_id)
    backlog_items = executor.load_backlog()

    # Get all Development/Infrastructure tasks
    dev_tasks = executor.filter_development_tasks(sprint_data, backlog_items)

    print(f"\nAll Development/Infrastructure tasks: {len(dev_tasks)}")

    # Custom filter: Only Development tasks (exclude Infrastructure)
    dev_only = [t for t in dev_tasks if t.get("task_type") == "Development"]
    print(f"Development only: {len(dev_only)}")

    # Custom filter: Only Infrastructure tasks
    infra_only = [t for t in dev_tasks if t.get("task_type") == "Infrastructure"]
    print(f"Infrastructure only: {len(infra_only)}")

    # Custom filter: Tasks with no dependencies
    no_deps = [t for t in dev_tasks if not t.get("dependencies")]
    print(f"Tasks with no dependencies: {len(no_deps)}")

    # Custom filter: Tasks with specific label
    integration_tasks = [t for t in dev_tasks if "integration" in t.get("labels", [])]
    print(f"Integration tasks: {len(integration_tasks)}")

    # Show filtered tasks
    print("\nIntegration tasks:")
    for task in integration_tasks:
        print(f"  - {task['id']}: {task['title']}")


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("Sprint Task Executor - Examples")
    print("=" * 80 + "\n")

    # Example 1: Preview
    example_1_preview_tasks()
    input("\nPress Enter to continue to Example 2...")

    # Example 2: Format
    example_2_format_task()
    input("\nPress Enter to continue to Example 3...")

    # Example 3: Execute Basic (async)
    asyncio.run(example_3_execute_sprint_basic())
    input("\nPress Enter to continue to Example 4...")

    # Example 4: Execute Advanced (async)
    asyncio.run(example_4_execute_sprint_advanced())
    input("\nPress Enter to continue to Example 5...")

    # Example 5: Execute Single Task (async)
    asyncio.run(example_5_execute_single_task())
    input("\nPress Enter to continue to Example 6...")

    # Example 6: Custom Filtering
    example_6_custom_filtering()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
