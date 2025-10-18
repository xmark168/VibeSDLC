"""
Advanced Sprint Task Executor

Script với nhiều options để customize execution.

Usage:
    # Preview tasks
    python run_sprint_advanced.py --preview
    
    # Execute với default settings
    python run_sprint_advanced.py --execute
    
    # Execute với custom settings
    python run_sprint_advanced.py --execute --sprint sprint-2 --model gpt-4o
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from agents.developer.agent import (
    execute_sprint,
    filter_development_tasks,
    SprintTaskExecutor,
)


def preview_sprint(sprint_id: str):
    """Preview tasks in a sprint."""
    print("=" * 80)
    print(f"📋 Preview: {sprint_id}")
    print("=" * 80)
    
    try:
        # Filter tasks
        tasks = filter_development_tasks(sprint_id)
        
        if not tasks:
            print("⚠️  No Development/Infrastructure tasks found")
            return
        
        print(f"\n🔍 Found {len(tasks)} Development/Infrastructure tasks:\n")
        
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task['id']}: {task['title']}")
            print(f"   Type: {task.get('task_type', 'N/A')}")
            print(f"   Estimate: {task.get('estimate_value', 'N/A')} hours")
            
            deps = task.get('dependencies', [])
            if deps:
                print(f"   Dependencies: {', '.join(deps)}")
            else:
                print(f"   Dependencies: None")
            print()
        
        # Show execution order
        print("=" * 80)
        print("📊 Execution Order (after dependency resolution):")
        print("=" * 80)
        
        executor = SprintTaskExecutor()
        sprint_data = executor.load_sprint(sprint_id)
        backlog_items = executor.load_backlog()
        dev_tasks = executor.filter_development_tasks(sprint_data, backlog_items)
        sorted_tasks = executor.resolve_dependencies(dev_tasks, backlog_items)
        
        for i, task in enumerate(sorted_tasks, 1):
            deps = task.get('dependencies', [])
            deps_str = f" (depends on: {', '.join(deps)})" if deps else ""
            print(f"{i}. {task['id']}: {task['title']}{deps_str}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def execute_sprint_tasks(
    sprint_id: str,
    working_dir: str,
    model: str,
    pgvector: bool,
    stop_on_error: bool,
):
    """Execute sprint tasks."""
    print("🚀 Starting Sprint Task Executor")
    print("=" * 80)
    print(f"📋 Sprint ID: {sprint_id}")
    print(f"📁 Working Directory: {working_dir}")
    print(f"🤖 Model: {model}")
    print(f"🔍 PGVector: {'Enabled' if pgvector else 'Disabled'}")
    print(f"⚙️  Stop on Error: {stop_on_error}")
    print("=" * 80)
    print()
    
    try:
        result = await execute_sprint(
            sprint_id=sprint_id,
            working_directory=working_dir,
            model_name=model,
            enable_pgvector=pgvector,
            continue_on_error=not stop_on_error,
        )
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Status: {result['status']}")
        print(f"Total Tasks: {result['tasks_total']}")
        print(f"Executed: {result['tasks_executed']}")
        print(f"✅ Succeeded: {result['tasks_succeeded']}")
        print(f"❌ Failed: {result['tasks_failed']}")
        print(f"⏱️  Duration: {result['duration_seconds']:.2f}s")
        print(f"🕐 Start Time: {result['start_time']}")
        print(f"🕐 End Time: {result['end_time']}")
        print("=" * 80)
        
        # Print individual task results
        if result['results']:
            print("\n📋 Task Results:")
            for task_result in result['results']:
                status_icon = "✅" if task_result['status'] == 'success' else "❌"
                print(f"  {status_icon} {task_result['task_id']}: {task_result['status']}")
                
                if task_result['status'] == 'success':
                    task_data = task_result.get('result', {})
                    if task_data.get('generated_files'):
                        print(f"     Generated: {len(task_data['generated_files'])} files")
                    if task_data.get('commit_history'):
                        print(f"     Commits: {len(task_data['commit_history'])}")
                else:
                    print(f"     Error: {task_result.get('error', 'Unknown error')}")
        
        # Exit code
        if result['tasks_failed'] > 0:
            print("\n⚠️  Some tasks failed. Check logs above.")
            sys.exit(1)
        else:
            print("\n🎉 All tasks completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Advanced Sprint Task Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview tasks
  python run_sprint_advanced.py --preview
  
  # Execute with defaults
  python run_sprint_advanced.py --execute
  
  # Execute with custom settings
  python run_sprint_advanced.py --execute --sprint sprint-2 --model gpt-4o
  
  # Execute and stop on first error
  python run_sprint_advanced.py --execute --stop-on-error
        """
    )
    
    # Mode
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--preview",
        action="store_true",
        help="Preview tasks without executing"
    )
    mode_group.add_argument(
        "--execute",
        action="store_true",
        help="Execute all tasks"
    )
    
    # Sprint configuration
    parser.add_argument(
        "--sprint",
        default="sprint-1",
        help="Sprint ID to execute (default: sprint-1)"
    )
    
    parser.add_argument(
        "--working-dir",
        default=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
        help="Working directory for code generation"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        choices=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        help="LLM model to use (default: gpt-4o-mini)"
    )
    
    parser.add_argument(
        "--no-pgvector",
        action="store_true",
        help="Disable pgvector indexing"
    )
    
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop execution on first task failure"
    )
    
    args = parser.parse_args()
    
    # Execute based on mode
    if args.preview:
        preview_sprint(args.sprint)
    else:
        asyncio.run(execute_sprint_tasks(
            sprint_id=args.sprint,
            working_dir=args.working_dir,
            model=args.model,
            pgvector=not args.no_pgvector,
            stop_on_error=args.stop_on_error,
        ))


if __name__ == "__main__":
    main()

