"""Test Langfuse tracing for analyze_and_plan node."""
import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add backend path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Load .env
from dotenv import load_dotenv
load_dotenv(backend_path / ".env")


async def test_analyze_with_langfuse():
    """Test analyze_and_plan with Langfuse tracing."""
    print("\n=== Testing Langfuse with analyze_and_plan ===\n")
    
    # Check env
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        print("[SKIP] LANGFUSE_PUBLIC_KEY not set")
        return False
    
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler
        from app.agents.developer_v2.src.nodes.analyze_and_plan import analyze_and_plan
        from app.agents.developer_v2.src.skills.registry import SkillRegistry
        
        # Setup Langfuse
        print("1. Setting up Langfuse...")
        langfuse_client = Langfuse()
        langfuse_span_ctx = langfuse_client.start_as_current_span(name="test_analyze_and_plan")
        langfuse_span_ctx.__enter__()
        
        langfuse_client.update_current_trace(
            user_id="test_user",
            session_id=str(uuid4()),
            input={"test": "analyze_and_plan"},
            tags=["test", "analyze_and_plan"],
        )
        
        trace_id = langfuse_client.get_current_trace_id()
        print(f"   Trace ID: {trace_id}")
        
        langfuse_handler = CallbackHandler()
        print(f"   Handler: {type(langfuse_handler).__name__}")
        
        # Create minimal test state
        print("\n2. Creating test state...")
        workspace_path = str(backend_path / "projects" / "test_langfuse")
        
        # Create workspace if not exists
        os.makedirs(workspace_path, exist_ok=True)
        
        # Create minimal package.json
        pkg_json = os.path.join(workspace_path, "package.json")
        if not os.path.exists(pkg_json):
            with open(pkg_json, "w") as f:
                f.write('{"name": "test", "version": "1.0.0"}')
        
        state = {
            "story_id": "TEST-001",
            "story_title": "Test story for Langfuse",
            "story_description": "Simple test",
            "story_requirements": ["Create a hello world page"],
            "workspace_path": workspace_path,
            "langfuse_handler": langfuse_handler,
            "langfuse_client": langfuse_client,
            "tech_stack": "nextjs",
            "skill_registry": SkillRegistry("nextjs"),
        }
        
        print(f"   Workspace: {workspace_path}")
        
        # Run analyze_and_plan
        print("\n3. Running analyze_and_plan...")
        print("   (This will make LLM calls - check Langfuse dashboard)")
        
        result = await analyze_and_plan(state)
        
        print(f"\n4. Result:")
        print(f"   - Steps: {result.get('total_steps', 0)}")
        print(f"   - Plan: {len(result.get('implementation_plan', []))} items")
        
        # Flush and close
        print("\n5. Flushing Langfuse...")
        langfuse_client.update_current_trace(output={
            "total_steps": result.get("total_steps", 0),
            "plan_count": len(result.get("implementation_plan", [])),
        })
        langfuse_span_ctx.__exit__(None, None, None)
        langfuse_client.flush()
        
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        print(f"\n[OK] Test completed!")
        print(f"   Check trace at: {host}/project/*/traces/{trace_id}")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_analyze_with_langfuse())
