"""
Langfuse Tracing Integration for Developer Agent

This module provides utilities for tracing and monitoring the developer agent's
execution flow using Langfuse. It includes:
- Automatic tracing via LangChain CallbackHandler
- Manual tracing decorators for custom spans
- Context managers for nested trace hierarchy
- Error handling and metadata capture

Quick Start:
    from app.utils.langfuse_tracer import get_callback_handler, trace_span

    # Get callback handler for automatic tracing
    handler = get_callback_handler(session_id="my-session")
    llm = ChatOpenAI(callbacks=[handler])

    # Use trace_span for manual tracing
    with trace_span("operation_name", metadata={"key": "value"}):
        # Your code here
        pass

Documentation:
    See LANGFUSE_INTEGRATION.md for full documentation
"""

import os
import functools
import time
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager
from langfuse import Langfuse
from langfuse.callback import CallbackHandler


# Initialize Langfuse client
def get_langfuse_client() -> Optional[Langfuse]:
    """
    Initialize and return Langfuse client with credentials from environment.

    Returns:
        Langfuse client instance or None if credentials are not configured
    """
    try:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not public_key or not secret_key:
            print("⚠️  Langfuse credentials not found in environment. Tracing disabled.")
            return None

        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

        print(f"✅ Langfuse client initialized successfully (host: {host})")
        return client

    except Exception as e:
        print(f"❌ Failed to initialize Langfuse client: {e}")
        return None


# Global Langfuse client instance
_langfuse_client = get_langfuse_client()


def get_callback_handler(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    trace_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[CallbackHandler]:
    """
    Create a Langfuse CallbackHandler for automatic tracing.

    This handler can be passed to LangChain components to automatically
    trace LLM calls, tool executions, and agent steps.

    Args:
        session_id: Optional session identifier
        user_id: Optional user identifier
        trace_name: Optional name for the trace
        metadata: Optional metadata to attach to the trace

    Returns:
        CallbackHandler instance or None if Langfuse is not configured

    Example:
        handler = get_callback_handler(
            session_id="dev-session-123",
            trace_name="implement-feature",
            metadata={"feature": "user-auth"}
        )
        llm = ChatOpenAI(callbacks=[handler])
    """
    if not _langfuse_client:
        return None

    try:
        handler = CallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            session_id=session_id,
            user_id=user_id,
            trace_name=trace_name,
            metadata=metadata,
        )
        return handler
    except Exception as e:
        print(f"❌ Failed to create Langfuse CallbackHandler: {e}")
        return None


@contextmanager
def trace_span(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    input_data: Optional[Any] = None,
    trace_id: Optional[str] = None,
    parent_observation_id: Optional[str] = None,
):
    """
    Context manager for creating manual trace spans.

    Use this to wrap code blocks that you want to trace with custom metadata.

    Args:
        name: Name of the span
        metadata: Optional metadata to attach
        input_data: Optional input data to log
        trace_id: Optional trace ID to attach this span to
        parent_observation_id: Optional parent observation ID for nesting

    Yields:
        Span object that can be used to add additional metadata

    Example:
        with trace_span("load_codebase", metadata={"path": "/src"}) as span:
            result = load_codebase("/src")
            span.output = result
    """
    if not _langfuse_client:
        # If Langfuse is not configured, just execute the code without tracing
        yield None
        return

    start_time = time.time()
    span = None

    try:
        # Create span
        if trace_id:
            trace = _langfuse_client.trace(id=trace_id)
            span = trace.span(
                name=name,
                metadata=metadata,
                input=input_data,
                parent_observation_id=parent_observation_id,
            )
        else:
            # Create a new trace with this span
            trace = _langfuse_client.trace(name=name, metadata=metadata)
            span = trace.span(
                name=name,
                metadata=metadata,
                input=input_data,
            )

        yield span

        # Mark as successful
        if span:
            span.end(
                metadata={
                    **(metadata or {}),
                    "duration_seconds": time.time() - start_time,
                }
            )

    except Exception as e:
        # Log error to span
        if span:
            span.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    **(metadata or {}),
                    "error": str(e),
                    "duration_seconds": time.time() - start_time,
                },
            )
        raise


def trace_function(
    name: Optional[str] = None,
    capture_input: bool = True,
    capture_output: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Decorator for tracing function executions.

    Args:
        name: Optional custom name for the trace (defaults to function name)
        capture_input: Whether to capture function arguments
        capture_output: Whether to capture function return value
        metadata: Optional metadata to attach

    Example:
        @trace_function(name="load_codebase", metadata={"type": "tool"})
        def load_codebase(path: str):
            return analyze_code(path)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _langfuse_client:
                return func(*args, **kwargs)

            span_name = name or func.__name__
            input_data = None

            if capture_input:
                input_data = {
                    "args": args,
                    "kwargs": kwargs,
                }

            with trace_span(
                name=span_name,
                metadata={**(metadata or {}), "function": func.__name__},
                input_data=input_data,
            ) as span:
                result = func(*args, **kwargs)

                if span and capture_output:
                    span.end(output=result)

                return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _langfuse_client:
                return await func(*args, **kwargs)

            span_name = name or func.__name__
            input_data = None

            if capture_input:
                input_data = {
                    "args": args,
                    "kwargs": kwargs,
                }

            with trace_span(
                name=span_name,
                metadata={**(metadata or {}), "function": func.__name__},
                input_data=input_data,
            ) as span:
                result = await func(*args, **kwargs)

                if span and capture_output:
                    span.end(output=result)

                return result

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_agent_state(
    state: Dict[str, Any],
    phase: str,
    trace_id: Optional[str] = None,
):
    """
    Log agent state at different phases of execution.

    Args:
        state: Agent state dictionary
        phase: Phase name (e.g., "initialization", "planning", "execution")
        trace_id: Optional trace ID to attach this log to
    """
    if not _langfuse_client:
        return

    try:
        metadata = {
            "phase": phase,
            "working_directory": state.get("working_directory"),
            "project_type": state.get("project_type"),
            "implementation_status": state.get("implementation_status"),
            "generated_files_count": len(state.get("generated_files", [])),
            "commit_count": len(state.get("commit_history", [])),
        }

        # Add todos info if available
        if "todos" in state:
            todos = state["todos"]
            metadata["todos_total"] = len(todos)
            metadata["todos_completed"] = sum(
                1 for t in todos if t.get("status") == "completed"
            )

        with trace_span(
            name=f"agent_state_{phase}",
            metadata=metadata,
            input_data={"phase": phase},
            trace_id=trace_id,
        ):
            pass  # Just log the state, no execution needed

    except Exception as e:
        print(f"⚠️  Failed to log agent state: {e}")


def flush_langfuse():
    """
    Flush any pending Langfuse events.

    Call this at the end of your application to ensure all traces are sent.
    """
    if _langfuse_client:
        try:
            _langfuse_client.flush()
            print("✅ Langfuse traces flushed successfully")
        except Exception as e:
            print(f"⚠️  Failed to flush Langfuse traces: {e}")
