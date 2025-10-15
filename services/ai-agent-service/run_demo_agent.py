#!/usr/bin/env python3
"""
Demo script to run the implementor agent
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app.agents.developer.implementor.agent import run_implementor

async def main():
    """Run the implementor agent demo"""
    
    # Set up paths
    working_directory = str(current_dir / "app" / "agents" / "demo")
    
    print("=" * 80)
    print("🚀 STARTING IMPLEMENTOR AGENT DEMO")
    print("=" * 80)
    print(f"Working Directory: {working_directory}")
    print(f"Request: Add JWT authentication to FastAPI application")
    print("=" * 80)
    
    # Verify the working directory exists
    if not os.path.exists(working_directory):
        print(f"❌ Error: Working directory does not exist: {working_directory}")
        return
    
    # List files in the working directory
    print("📁 Files in working directory:")
    for file in os.listdir(working_directory):
        file_path = os.path.join(working_directory, file)
        if os.path.isfile(file_path):
            print(f"  - {file}")
    print()
    
    try:
        # Run the implementor agent
        result = await run_implementor(
            user_request="Add user authentication with JWT tokens to the FastAPI application. Include user registration, login endpoints, JWT token generation and validation, and protect existing user endpoints with authentication middleware.",
            working_directory=working_directory,
            project_type="existing",
            enable_pgvector=True,
        )

        print("=" * 80)
        print("🎉 IMPLEMENTATION RESULTS")
        print("=" * 80)
        print(f"Status: {result.get('implementation_status', 'Unknown')}")
        print(f"Generated Files: {len(result.get('generated_files', []))}")
        print(f"Commits: {len(result.get('commit_history', []))}")

        if "generated_files" in result and result["generated_files"]:
            print("\n📄 Generated Files:")
            for file_info in result["generated_files"]:
                print(f"  - {file_info}")

        if "commit_history" in result and result["commit_history"]:
            print("\n📝 Commit History:")
            for commit in result["commit_history"]:
                print(f"  - {commit}")

        if "todos" in result and result["todos"]:
            print("\n✅ Todos:")
            for i, todo in enumerate(result["todos"], 1):
                status = todo.get("status", "unknown")
                content = todo.get("content", "No content")
                print(f"  {i}. [{status}] {content}")

        if "error" in result:
            print(f"\n❌ Error: {result['error']}")

        print("\n" + "=" * 80)
        print("🏁 DEMO COMPLETED")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error running implementor agent: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
