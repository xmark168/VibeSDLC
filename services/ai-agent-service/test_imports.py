"""
Test Sprint Task Executor Imports

Simple script to verify that Sprint Task Executor can be imported from agent.py
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

print("Testing imports from agents.developer.agent...")

try:
    from agents.developer.agent import (
        SprintTaskExecutor,
        execute_sprint,
        filter_development_tasks,
        format_task_as_request,
    )
    
    print("✅ All imports successful!")
    print(f"   - SprintTaskExecutor: {SprintTaskExecutor}")
    print(f"   - execute_sprint: {execute_sprint}")
    print(f"   - filter_development_tasks: {filter_development_tasks}")
    print(f"   - format_task_as_request: {format_task_as_request}")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

print("\n✅ Sprint Task Executor successfully integrated into agent.py!")

