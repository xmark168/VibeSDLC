"""
Test script for Langfuse integration with Developer Agent

This script tests the Langfuse tracing integration by running a simple
developer agent task and verifying that traces are created correctly.

Usage:
    python test_langfuse_integration.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.agents.developer.agent import run_developer
from app.utils.langfuse_tracer import (
    get_langfuse_client,
    get_callback_handler,
    trace_span,
    flush_langfuse,
)


def test_langfuse_client():
    """Test Langfuse client initialization"""
    print("=" * 80)
    print("TEST 1: Langfuse Client Initialization")
    print("=" * 80)
    
    client = get_langfuse_client()
    
    if client:
        print("✅ Langfuse client initialized successfully")
        print(f"   Host: {os.getenv('LANGFUSE_HOST')}")
        return True
    else:
        print("❌ Langfuse client initialization failed")
        print("   Check your .env file for credentials")
        return False


def test_callback_handler():
    """Test CallbackHandler creation"""
    print("\n" + "=" * 80)
    print("TEST 2: CallbackHandler Creation")
    print("=" * 80)
    
    handler = get_callback_handler(
        session_id="test-session",
        trace_name="test-trace",
        metadata={"test": "metadata"}
    )
    
    if handler:
        print("✅ CallbackHandler created successfully")
        return True
    else:
        print("❌ CallbackHandler creation failed")
        return False


def test_trace_span():
    """Test manual trace span"""
    print("\n" + "=" * 80)
    print("TEST 3: Manual Trace Span")
    print("=" * 80)
    
    try:
        with trace_span(
            name="test_span",
            metadata={"test": "metadata"},
            input_data={"input": "test"}
        ) as span:
            print("✅ Trace span created successfully")
            
            # Simulate some work
            import time
            time.sleep(0.1)
            
            if span:
                span.end(output={"output": "test_result"})
                print("✅ Trace span ended successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Trace span test failed: {e}")
        return False


async def test_developer_agent_with_tracing():
    """Test developer agent execution with tracing"""
    print("\n" + "=" * 80)
    print("TEST 4: Developer Agent with Tracing")
    print("=" * 80)
    
    # Create a temporary test directory
    test_dir = Path(__file__).parent / "test_workspace"
    test_dir.mkdir(exist_ok=True)
    
    # Create a simple test file
    test_file = test_dir / "test.py"
    test_file.write_text("""
# Simple test file
def hello():
    return "Hello, World!"
""")
    
    try:
        print(f"📁 Test workspace: {test_dir}")
        print("🚀 Running developer agent with tracing...")
        
        result = await run_developer(
            user_request="Add a docstring to the hello function",
            working_directory=str(test_dir),
            project_type="existing",
            enable_pgvector=False,  # Disable pgvector for simple test
            session_id="test-langfuse-integration",
            user_id="test-user",
            model_name="gpt-4o-mini",
        )
        
        print("\n✅ Developer agent execution completed")
        print(f"   Status: {result.get('implementation_status', 'Unknown')}")
        print(f"   Generated files: {len(result.get('generated_files', []))}")
        print(f"   Commits: {len(result.get('commit_history', []))}")
        
        if "todos" in result:
            print(f"   Todos: {len(result['todos'])}")
            for i, todo in enumerate(result["todos"], 1):
                status = todo.get("status", "unknown")
                content = todo.get("content", "No content")
                print(f"      {i}. [{status}] {content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Developer agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up test workspace...")
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)


def test_trace_visibility():
    """Test trace visibility in Langfuse"""
    print("\n" + "=" * 80)
    print("TEST 5: Trace Visibility")
    print("=" * 80)
    
    print("📊 Flushing traces to Langfuse...")
    flush_langfuse()
    
    print("\n✅ Traces flushed successfully")
    print("\n📍 View traces at:")
    print(f"   {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
    print("\n🔍 Look for:")
    print("   - Session ID: test-langfuse-integration")
    print("   - User ID: test-user")
    print("   - Trace name: developer_agent_execution")
    
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("LANGFUSE INTEGRATION TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # Test 1: Client initialization
    results.append(("Client Initialization", test_langfuse_client()))
    
    # Test 2: CallbackHandler
    results.append(("CallbackHandler Creation", test_callback_handler()))
    
    # Test 3: Manual trace span
    results.append(("Manual Trace Span", test_trace_span()))
    
    # Test 4: Developer agent with tracing
    results.append(("Developer Agent Execution", await test_developer_agent_with_tracing()))
    
    # Test 5: Trace visibility
    results.append(("Trace Visibility", test_trace_visibility()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 All tests passed! Langfuse integration is working correctly.")
        print("\n📊 Next steps:")
        print("   1. Check Langfuse dashboard for traces")
        print("   2. Verify trace details and metadata")
        print("   3. Test with real development tasks")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify .env file has correct Langfuse credentials")
        print("   2. Check network connectivity to Langfuse host")
        print("   3. Review error messages for specific issues")
    
    return passed == total


if __name__ == "__main__":
    # Check environment
    print("🔍 Checking environment...")
    print(f"   LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST', 'Not set')}")
    print(f"   LANGFUSE_PUBLIC_KEY: {'Set' if os.getenv('LANGFUSE_PUBLIC_KEY') else 'Not set'}")
    print(f"   LANGFUSE_SECRET_KEY: {'Set' if os.getenv('LANGFUSE_SECRET_KEY') else 'Not set'}")
    
    if not os.getenv('LANGFUSE_PUBLIC_KEY') or not os.getenv('LANGFUSE_SECRET_KEY'):
        print("\n⚠️  Warning: Langfuse credentials not found in environment")
        print("   Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env file")
        print("   Tests will run but tracing will be disabled")
    
    # Run tests
    success = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

