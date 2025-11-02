"""
Example: Using Langfuse Tracing with Developer Agent

This example demonstrates how to use Langfuse tracing to monitor
and debug the developer agent's execution flow.

Features demonstrated:
- Basic agent execution with automatic tracing
- Custom session and user IDs
- Viewing trace information
- Error handling with tracing
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.agents.developer.agent import run_developer
from app.utils.langfuse_tracer import (
    trace_span,
    log_agent_state,
    flush_langfuse,
)


async def example_1_basic_tracing():
    """
    Example 1: Basic agent execution with automatic tracing

    This is the simplest way to use Langfuse tracing.
    Just call run_developer() and tracing happens automatically.
    """
    print("=" * 80)
    print("EXAMPLE 1: Basic Tracing")
    print("=" * 80)

    result = await run_developer(
        user_request="Create a simple FastAPI endpoint for health check",
        working_directory="./demo_project",
        project_type="new",
        enable_pgvector=False,
    )

    print("\n✅ Execution completed")
    print(f"📊 Check Langfuse dashboard for traces")
    print(f"   Session ID: {result.get('session_id', 'auto-generated')}")

    return result


async def example_2_custom_session():
    """
    Example 2: Using custom session and user IDs

    Custom IDs help you organize and filter traces in Langfuse.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Custom Session and User IDs")
    print("=" * 80)

    # Use meaningful session IDs
    session_id = "feature-auth-2024-01-15"
    user_id = "developer-john"

    result = await run_developer(
        user_request="Add JWT authentication to the API",
        working_directory="./demo_project",
        project_type="existing",
        session_id=session_id,
        user_id=user_id,
    )

    print(f"\n✅ Execution completed")
    print(f"📊 Find this trace in Langfuse:")
    print(f"   Session ID: {session_id}")
    print(f"   User ID: {user_id}")

    return result


async def example_3_custom_tracing():
    """
    Example 3: Adding custom trace spans

    You can add your own trace spans around specific operations
    for more detailed monitoring.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Custom Trace Spans")
    print("=" * 80)

    # Wrap your operation in a custom trace span
    with trace_span(
        name="feature_implementation",
        metadata={
            "feature": "user-profile",
            "priority": "high",
            "estimated_time": "30min",
        },
        input_data={"requirements": "User profile CRUD operations"},
    ) as span:

        result = await run_developer(
            user_request="Implement user profile CRUD endpoints",
            working_directory="./demo_project",
            project_type="existing",
            session_id="feature-profile-implementation",
        )

        # Add output to span
        if span:
            span.end(
                output={
                    "status": result.get("implementation_status"),
                    "files_generated": len(result.get("generated_files", [])),
                    "commits": len(result.get("commit_history", [])),
                }
            )

    print("\n✅ Execution completed with custom tracing")

    return result


async def example_4_error_handling():
    """
    Example 4: Error handling with tracing

    Errors are automatically captured in traces, making debugging easier.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Error Handling with Tracing")
    print("=" * 80)

    try:
        # This might fail if directory doesn't exist
        result = await run_developer(
            user_request="Add database migrations",
            working_directory="/nonexistent/directory",
            project_type="existing",
            session_id="error-handling-demo",
        )

        print("\n✅ Execution completed")
        return result

    except Exception as e:
        print(f"\n❌ Execution failed: {e}")
        print(f"📊 Error details captured in Langfuse trace")
        print(f"   Session ID: error-handling-demo")

        # Error is automatically logged to Langfuse
        # You can view the full stack trace in the dashboard

        return None


async def example_5_monitoring_workflow():
    """
    Example 5: Monitoring specific workflow phases

    Track different phases of the agent workflow separately.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Monitoring Workflow Phases")
    print("=" * 80)

    session_id = "workflow-monitoring-demo"

    # Phase 1: Planning
    with trace_span(
        name="planning_phase", metadata={"phase": "planning", "session": session_id}
    ):
        print("📋 Planning phase...")
        # Planning happens automatically in run_developer

    # Phase 2: Implementation
    with trace_span(
        name="implementation_phase",
        metadata={"phase": "implementation", "session": session_id},
    ):
        print("🔨 Implementation phase...")
        result = await run_developer(
            user_request="Add logging middleware to FastAPI",
            working_directory="./demo_project",
            project_type="existing",
            session_id=session_id,
        )

    # Phase 3: Review
    with trace_span(
        name="review_phase", metadata={"phase": "review", "session": session_id}
    ):
        print("🔍 Review phase...")
        # Review logic here
        log_agent_state(result, "review_complete")

    print("\n✅ All phases completed and traced")
    print(f"📊 View workflow breakdown in Langfuse")

    return result


async def example_6_batch_operations():
    """
    Example 6: Tracing multiple operations

    Track multiple related operations in a single session.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Batch Operations Tracing")
    print("=" * 80)

    session_id = "batch-operations-demo"
    operations = [
        "Add user model",
        "Add user endpoints",
        "Add user tests",
    ]

    results = []

    for i, operation in enumerate(operations, 1):
        with trace_span(
            name=f"operation_{i}",
            metadata={
                "session": session_id,
                "operation": operation,
                "sequence": i,
            },
        ):
            print(f"\n🔄 Operation {i}/{len(operations)}: {operation}")

            result = await run_developer(
                user_request=operation,
                working_directory="./demo_project",
                project_type="existing",
                session_id=f"{session_id}-op{i}",
            )

            results.append(result)

    print(f"\n✅ All {len(operations)} operations completed")
    print(f"📊 View batch execution in Langfuse")

    return results


async def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("LANGFUSE TRACING EXAMPLES")
    print("=" * 80)
    print("\nThese examples demonstrate various ways to use Langfuse tracing")
    print("with the Developer Agent.\n")

    # Choose which examples to run
    examples = [
        ("Basic Tracing", example_1_basic_tracing),
        ("Custom Session IDs", example_2_custom_session),
        ("Custom Trace Spans", example_3_custom_tracing),
        ("Error Handling", example_4_error_handling),
        ("Workflow Monitoring", example_5_monitoring_workflow),
        ("Batch Operations", example_6_batch_operations),
    ]

    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning Example 1 (Basic Tracing)...")
    print("To run other examples, modify the main() function.\n")

    # Run example 1 by default
    # Uncomment others to run them

    await example_1_basic_tracing()
    # await example_2_custom_session()
    # await example_3_custom_tracing()
    # await example_4_error_handling()
    # await example_5_monitoring_workflow()
    # await example_6_batch_operations()

    # Flush all traces
    print("\n" + "=" * 80)
    print("Flushing traces to Langfuse...")
    flush_langfuse()

    print("\n✅ All examples completed!")
    print("\n📊 View traces in Langfuse dashboard:")
    print("   https://langfuse.vibesdlc.com")
    print("\n💡 Tips:")
    print("   - Use session IDs to group related operations")
    print("   - Add metadata for better filtering and analysis")
    print("   - Check execution times to identify bottlenecks")
    print("   - Review error traces for debugging")


if __name__ == "__main__":
    asyncio.run(main())
