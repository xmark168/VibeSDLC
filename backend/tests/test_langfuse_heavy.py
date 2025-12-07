import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

def test_langfuse_heavy():
    """Test Langfuse with large payload (simulate real usage)."""
    from langfuse import Langfuse
    
    print(f"LANGFUSE_BASE_URL: {os.getenv('LANGFUSE_BASE_URL')}")
    
    client = Langfuse()
    
    # Large input (simulate file content)
    large_content = "x" * 50000  # 50KB
    
    # Create spans with large data
    for i in range(5):
        with client.start_as_current_span(name=f"span-{i}") as span:
            span.update(
                input={"content": large_content, "index": i},
                output={"result": f"processed-{i}", "data": large_content[:10000]}
            )
        print(f"Span {i} created")
    
    # Flush all
    print("Flushing...")
    client.flush()
    print("✅ Heavy test passed!")

if __name__ == "__main__":
    test_langfuse_heavy()
