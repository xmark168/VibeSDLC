import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from langfuse import Langfuse

from agents.product_owner.gatherer_agent import GathererAgent

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
    """Test the gatherer agent with a sample product requirement."""
    print_separator()
    print("Testing Gatherer Agent")
    print_separator()

    # Generate session and user IDs for tracking
    session_id = f"test-session-{uuid.uuid4()}"
    user_id = "test-user"

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")

    # Start a span for the test
    test_span = langfuse.start_span(
        name="gatherer_agent_test",
        metadata={
            "test_type": "integration",
            "environment": os.getenv("APP_ENV", "development"),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_id": user_id,
        },
    )

    # Initialize the agent with tracking IDs
    print("\nInitializing Gatherer Agent...")
    agent = GathererAgent(session_id=session_id, user_id=user_id)
    print("Agent initialized successfully")

    # Test case
    initial_context = "Build an AI-powered task management app"

    print(f"\nInitial Context: {initial_context}")
    print_separator()

    # Run the agent
    print("Running Gatherer Agent workflow...\n")

    try:
        # Log start of execution
        langfuse.create_event(
            name="test_execution_started",
            metadata={
                "session_id": session_id,
                "user_id": user_id,
                "initial_context": initial_context,
            },
        )

        result = agent.run(
            initial_context=initial_context,
            trace_name="gatherer_agent_test_run",
        )

        print_separator()
        print("Workflow completed successfully!")
        print_separator()

        # Extract the final state from the result
        final_node_state = None
        if isinstance(result, dict):
            for key, value in result.items():
                final_node_state = value

        if final_node_state:
            print("Final State (JSON):")
            print(json.dumps(final_node_state, indent=2, default=str))

            # End test span with results
            test_span.end(
                output=final_node_state,
                metadata={
                    "test_type": "integration",
                    "environment": os.getenv("APP_ENV", "development"),
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "final_state": final_node_state.get("status") if final_node_state else "unknown",
                },
            )

            # Log success event
            langfuse.create_event(
                name="test_execution_completed",
                metadata={
                    "session_id": session_id,
                    "user_id": user_id,
                    "status": "success",
                    "final_state": final_node_state.get("status") if final_node_state else "unknown",
                },
            )
        else:
            print("No final state found in result")
            print("Result:", result)

            # Log warning
            langfuse.create_event(
                name="test_execution_warning",
                level="WARNING",
                metadata={
                    "session_id": session_id,
                    "user_id": user_id,
                    "warning": "No final state found in result",
                },
            )

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback

        traceback.print_exc()

        # End span with error
        test_span.end(
            level="ERROR",
            status_message=str(e),
            metadata={
                "test_type": "integration",
                "environment": os.getenv("APP_ENV", "development"),
                "timestamp": datetime.now().isoformat(),
                "status": "error",
            },
        )

        # Log error event
        langfuse.create_event(
            name="test_execution_failed",
            level="ERROR",
            metadata={
                "session_id": session_id,
                "user_id": user_id,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
        )

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