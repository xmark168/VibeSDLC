"""
Test Script for Sprint Task Executor

This script demonstrates how to use the Sprint Task Executor to automatically
execute Development/Infrastructure tasks from a sprint backlog.

Usage:
    # Preview tasks that would be executed
    python test_sprint_execution.py --preview sprint-1

    # Execute all tasks in a sprint
    python test_sprint_execution.py --execute sprint-1 --working-dir ./target_project

    # Execute with custom model
    python test_sprint_execution.py --execute sprint-1 --model gpt-4o
"""

import asyncio
import argparse
import json
from pathlib import Path

# Add app to path
import sys

sys.path.insert(0, str(Path(__file__).parent / "app"))

from agents.developer.agent import (
    execute_sprint,
    filter_development_tasks,
    format_task_as_request,
)


def preview_tasks(sprint_id: str):
    """Preview which tasks would be executed."""
    print("=" * 80)
    print(f"📋 Preview: Development/Infrastructure Tasks in {sprint_id}")
    print("=" * 80)

    try:
        tasks = filter_development_tasks(sprint_id)

        if not tasks:
            print("⚠️  No Development/Infrastructure tasks found in this sprint")
            return

        print(f"\nFound {len(tasks)} tasks to execute:\n")

        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task['id']}: {task['title']}")
            print(
                f"   Type: {task['type']} | Task Type: {task.get('task_type', 'N/A')}"
            )
            print(f"   Status: {task['status']}")

            if task.get("dependencies"):
                print(f"   Dependencies: {', '.join(task['dependencies'])}")

            if task.get("estimate_value"):
                print(f"   Estimate: {task['estimate_value']} hours")

            print()

        # Show formatted request for first task
        if tasks:
            print("=" * 80)
            print("📝 Example: Formatted Request for First Task")
            print("=" * 80)
            print(format_task_as_request(tasks[0]))
            print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def execute_sprint_tasks(
    sprint_id: str,
    working_directory: str = ".",
    model_name: str = "gpt-4o-mini",
    enable_pgvector: bool = True,
    continue_on_error: bool = True,
):
    """Execute all Development/Infrastructure tasks in a sprint."""
    print("=" * 80)
    print(f"🚀 Executing Sprint: {sprint_id}")
    print("=" * 80)
    print(f"Working Directory: {working_directory}")
    print(f"Model: {model_name}")
    print(f"PGVector: {'Enabled' if enable_pgvector else 'Disabled'}")
    print(f"Continue on Error: {continue_on_error}")
    print("=" * 80)
    print()

    try:
        result = await execute_sprint(
            sprint_id=sprint_id,
            working_directory=working_directory,
            model_name=model_name,
            enable_pgvector=enable_pgvector,
            continue_on_error=continue_on_error,
        )

        # Save results to file
        output_file = f"sprint_execution_results_{sprint_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Results saved to: {output_file}")

        # Print detailed results
        print("\n" + "=" * 80)
        print("📊 Detailed Results")
        print("=" * 80)

        for task_result in result["results"]:
            task_id = task_result["task_id"]
            status = task_result["status"]

            if status == "success":
                print(f"✅ {task_id}: SUCCESS")
                dev_result = task_result.get("result", {})
                print(
                    f"   Implementation Status: {dev_result.get('implementation_status', 'N/A')}"
                )
                print(
                    f"   Generated Files: {len(dev_result.get('generated_files', []))}"
                )
                print(f"   Commits: {len(dev_result.get('commit_history', []))}")
            else:
                print(f"❌ {task_id}: FAILED")
                print(f"   Error: {task_result.get('error', 'Unknown error')}")

            print()

        return result

    except Exception as e:
        print(f"❌ Fatal Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sprint Task Executor - Automate Developer Agent execution for sprint tasks"
    )

    parser.add_argument("sprint_id", help="Sprint ID to process (e.g., sprint-1)")

    parser.add_argument(
        "--preview", action="store_true", help="Preview tasks without executing"
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute all Development/Infrastructure tasks",
    )

    parser.add_argument(
        "--working-dir",
        default=".",
        help="Working directory for Developer Agent (default: current directory)",
    )

    parser.add_argument(
        "--model", default="gpt-4o-mini", help="LLM model to use (default: gpt-4o-mini)"
    )

    parser.add_argument(
        "--no-pgvector", action="store_true", help="Disable pgvector indexing"
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop execution if a task fails (default: continue)",
    )

    args = parser.parse_args()

    # Default to preview if neither preview nor execute is specified
    if not args.preview and not args.execute:
        args.preview = True

    # Preview mode
    if args.preview:
        preview_tasks(args.sprint_id)

    # Execute mode
    if args.execute:
        asyncio.run(
            execute_sprint_tasks(
                sprint_id=args.sprint_id,
                working_directory=args.working_dir,
                model_name=args.model,
                enable_pgvector=not args.no_pgvector,
                continue_on_error=not args.stop_on_error,
            )
        )


if __name__ == "__main__":
    main()
