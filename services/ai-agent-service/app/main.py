import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from langfuse import Langfuse

from agents.product_owner.gatherer.graph import build_graph

# Load environment variables
load_dotenv()

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def test_gatherer_agent():
    """Test the graph-based gatherer with a sample product requirement."""
    print_separator()
    print("Testing Gatherer Agent")
    print_separator()

    # Generate session and user IDs for tracking
    session_id = f"test-session-{uuid.uuid4()}"
    user_id = os.getenv("LF_USER_ID", "test-user")

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")

    # Initialize graph-based workflow
    print("\nInitializing Gatherer Graph...")
    app, _ = build_graph()
    print("Graph initialized successfully")

    # Test case
    initial_context = """Tôi muốn xây dựng một ứng dụng quản lý công việc thông minh sử dụng AI.

Ứng dụng này sẽ giúp người dùng quản lý task hàng ngày hiệu quả hơn.
Mục tiêu chính là tự động ưu tiên công việc dựa trên deadline và mức độ quan trọng."""

    print(f"\nNgữ cảnh ban đầu: {initial_context}")
    print_separator()

    # Run the graph once with initial input
    print("Running Gatherer Graph workflow...\n")

    try:
        state = {"last_user_input": initial_context}
        result = app.invoke(
            state,
            config={
                "configurable": {"thread_id": session_id},
                "recursion_limit": 8,
            },
            start_at="initialize",
        )

        print_separator()
        print("Workflow completed successfully!")
        print_separator()

        print("Final State (JSON):")
        print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Flush all events to Langfuse
        langfuse.flush()

    print_separator()
    return True


def main():
    """Main function."""
    print("\nProduct Owner Agent Test Suite")

    success = test_gatherer_agent()

    if success:
        print("\nAll tests completed successfully!")
        return 0
    else:
        print("\nTests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())