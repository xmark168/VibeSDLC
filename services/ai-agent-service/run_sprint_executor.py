"""
Run Sprint Task Executor

Script để chạy Sprint Task Executor cho sprint-1 với working directory tùy chỉnh.

Usage:
    python run_sprint_executor.py
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from agents.developer.agent import execute_sprint


async def main():
    """Execute sprint-1 tasks."""
    
    print("🚀 Starting Sprint Task Executor")
    print("=" * 80)
    
    # Configuration
    sprint_id = "sprint-1"
    working_directory = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
    model_name = "gpt-4o-mini"  # Hoặc "gpt-4o" cho model mạnh hơn
    enable_pgvector = True
    continue_on_error = True  # Tiếp tục nếu 1 task fail
    
    print(f"📋 Sprint ID: {sprint_id}")
    print(f"📁 Working Directory: {working_directory}")
    print(f"🤖 Model: {model_name}")
    print(f"🔍 PGVector: {'Enabled' if enable_pgvector else 'Disabled'}")
    print(f"⚙️  Continue on Error: {continue_on_error}")
    print("=" * 80)
    print()
    
    # Execute sprint
    try:
        result = await execute_sprint(
            sprint_id=sprint_id,
            working_directory=working_directory,
            model_name=model_name,
            enable_pgvector=enable_pgvector,
            continue_on_error=continue_on_error,
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
        print("=" * 80)
        
        # Print individual task results
        if result['results']:
            print("\n📋 Task Results:")
            for task_result in result['results']:
                status_icon = "✅" if task_result['status'] == 'success' else "❌"
                print(f"  {status_icon} {task_result['task_id']}: {task_result['status']}")
                
                if task_result['status'] == 'failed':
                    print(f"     Error: {task_result.get('error', 'Unknown error')}")
        
        # Exit code
        if result['tasks_failed'] > 0:
            print("\n⚠️  Some tasks failed. Check logs above.")
            sys.exit(1)
        else:
            print("\n🎉 All tasks completed successfully!")
            sys.exit(0)
            
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure sprint.json and backlog.json exist in:")
        print("  app/agents/product_owner/")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

