"""Quick test to verify Langfuse integration works correctly."""
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

def test_langfuse_connection():
    """Test basic Langfuse connection and trace creation."""
    print("\n=== Testing Langfuse Integration ===\n")
    
    # Check env vars
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    print(f"LANGFUSE_HOST: {host}")
    print(f"LANGFUSE_PUBLIC_KEY: {'*' * 10 + public_key[-4:] if public_key else 'NOT SET'}")
    print(f"LANGFUSE_SECRET_KEY: {'*' * 10 + secret_key[-4:] if secret_key else 'NOT SET'}")
    
    if not public_key or not secret_key:
        print("\n[FAIL] Langfuse credentials not set in .env")
        return False
    
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler
        
        print("\n1. Creating Langfuse client...")
        client = Langfuse()
        
        print("2. Creating trace with start_as_current_span...")
        with client.start_as_current_span(name="test_langfuse_integration") as span:
            client.update_current_trace(
                user_id="test_user",
                session_id=str(uuid4()),
                input={"test": "input"},
                tags=["test", "integration"],
                metadata={"source": "test_script"}
            )
            trace_id = client.get_current_trace_id()
            print(f"   Trace ID: {trace_id}")
            
            print("3. Creating CallbackHandler...")
            handler = CallbackHandler()
            print(f"   Handler created: {type(handler).__name__}")
            
            print("4. Updating trace output...")
            client.update_current_trace(output={"status": "completed", "test": True})
        
        print("5. Flushing to Langfuse...")
        client.flush()
        
        print("\n[OK] Langfuse integration test PASSED!")
        print(f"   Check trace at: {host}/project/*/traces/{trace_id}")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Langfuse test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_langfuse_with_llm():
    """Test Langfuse with actual LLM call."""
    print("\n=== Testing Langfuse with LLM ===\n")
    
    try:
        from langfuse.langchain import CallbackHandler
        from langchain_anthropic import ChatAnthropic
        
        trace_id = str(uuid4())
        handler = CallbackHandler(
            trace_id=trace_id,
            user_id="test_user",
            tags=["test", "llm"]
        )
        
        print(f"Trace ID: {trace_id}")
        print("Making LLM call...")
        
        llm = ChatAnthropic(model="claude-3-5-haiku-20241022", max_tokens=100)
        response = llm.invoke(
            "Say 'Langfuse test successful!' in exactly 5 words.",
            config={"callbacks": [handler]}
        )
        
        print(f"LLM Response: {response.content}")
        handler.flush()
        
        print(f"\n[OK] LLM test PASSED!")
        print(f"   Check trace at: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}/project/*/traces/{trace_id}")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] LLM test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    
    # Test 1: Basic connection
    result1 = test_langfuse_connection()
    
    # Test 2: With LLM (optional)
    if result1 and "--llm" in sys.argv:
        test_langfuse_with_llm()
    
    print("\n" + "=" * 50)
