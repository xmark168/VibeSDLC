# app/agents/developer/implementor/agent.py
"""
Code Implementor Agent using DeepAgents

This agent implements features based on user requirements using the deepagents library.
It replaces the separate planner subagent by leveraging deepagents' built-in planning capabilities.

Key differences from separate planner approach:
- Uses deepagents' built-in write_todos for planning
- No manual graph construction - DeepAgents handles workflow
- Simpler state management with automatic persistence
- Built-in subagent support with isolated contexts
- Automatic human-in-the-loop support
"""

from deepagents import create_deep_agent
from typing import Dict, Any
import os
import sys


try:
    from langchain_openai import ChatOpenAI, OpenAI

    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: langchain_openai import failed: {e}")
    print("Using mock ChatOpenAI for development")
    LANGCHAIN_OPENAI_AVAILABLE = False

    # Mock ChatOpenAI class for development
    class ChatOpenAI:
        def __init__(self, **kwargs):
            self.model = kwargs.get("model", "gpt-4o-mini")
            self.temperature = kwargs.get("temperature", 0.1)
            print(f"Mock ChatOpenAI initialized with model: {self.model}")

        def invoke(self, messages):
            return {"content": "Mock response from ChatOpenAI"}

        def stream(self, messages):
            yield {"content": "Mock streaming response from ChatOpenAI"}


from dotenv import load_dotenv

load_dotenv()
AGENT_ROUTER_URL = os.getenv("OPENAI_BASE_URL")
AGENT_ROUTER_KEY = os.getenv("OPENAI_API_KEY")

# Import Langfuse tracing utilities
try:
    from app.utils.langfuse_tracer import (
        get_callback_handler,
        trace_span,
        log_agent_state,
        flush_langfuse,
    )

    LANGFUSE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Langfuse tracing not available: {e}")
    LANGFUSE_AVAILABLE = False

    # Mock functions if import fails
    def get_callback_handler(*args, **kwargs):
        return None

    def trace_span(*args, **kwargs):
        from contextlib import contextmanager

        @contextmanager
        def dummy():
            yield None

        return dummy()

    def log_agent_state(*args, **kwargs):
        pass

    def flush_langfuse():
        pass


# Handle both package import and direct execution
if __name__ == "__main__":
    # Direct execution - add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from instructions import get_implementor_instructions
    from agents.developer.implementor.tools import (
        load_codebase_tool,
        index_codebase_tool,
        search_similar_code_tool,
        sync_virtual_to_disk_tool,
        list_virtual_files_tool,
        detect_stack_tool,
        retrieve_boilerplate_tool,
        create_feature_branch_tool,
        select_integration_strategy_tool,
        generate_code_tool,
        commit_changes_tool,
        create_pull_request_tool,
        collect_feedback_tool,
        refine_code_tool,
    )
    from agents.developer.implementor.subagents import code_generator_subagent
else:
    # Package import - use relative imports
    from .instructions import get_implementor_instructions
    from agents.developer.implementor.tools import (
        load_codebase_tool,
        index_codebase_tool,
        search_similar_code_tool,
        sync_virtual_to_disk_tool,
        list_virtual_files_tool,
        detect_stack_tool,
        retrieve_boilerplate_tool,
        create_feature_branch_tool,
        select_integration_strategy_tool,
        generate_code_tool,
        commit_changes_tool,
        create_pull_request_tool,
        collect_feedback_tool,
        refine_code_tool,
    )
    from agents.developer.implementor.subagents import code_generator_subagent


def create_developer_agent(
    working_directory: str = ".",
    project_type: str = "existing",  # "new" or "existing"
    enable_pgvector: bool = True,
    boilerplate_templates_path: str = None,
    model_name: str = "gpt-4o-mini",
    session_id: str = None,
    user_id: str = None,
    **config,
):
    """
    Create a DeepAgents-based implementor agent with Langfuse tracing.

    Args:
        working_directory: Working directory for the agent
        project_type: "new" for new projects, "existing" for existing codebases
        enable_pgvector: Whether to enable pgvector indexing
        boilerplate_templates_path: Path to boilerplate templates
        model_name: LLM model to use
        session_id: Optional session ID for Langfuse tracing
        user_id: Optional user ID for Langfuse tracing
        **config: Additional configuration options

    Returns:
        Compiled DeepAgent ready for invocation
    """

    # Set default boilerplate path if not provided
    if boilerplate_templates_path is None:
        boilerplate_templates_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "templates", "boilerplate"
        )

    # Get implementor instructions
    instructions = get_implementor_instructions(
        working_directory=working_directory,
        project_type=project_type,
        enable_pgvector=enable_pgvector,
        boilerplate_templates_path=boilerplate_templates_path,
    )

    # Create Langfuse callback handler for automatic tracing
    langfuse_handler = None
    if LANGFUSE_AVAILABLE:
        langfuse_handler = get_callback_handler(
            session_id=session_id,
            user_id=user_id,
            trace_name="developer_agent_execution",
            metadata={
                "working_directory": working_directory,
                "project_type": project_type,
                "model_name": model_name,
                "enable_pgvector": enable_pgvector,
            },
        )
        if langfuse_handler:
            print(f"✅ Langfuse tracing enabled for session: {session_id or 'default'}")

    # Initialize LLM with Langfuse callback
    callbacks = [langfuse_handler] if langfuse_handler else []

    llm = ChatOpenAI(
        model_name=model_name,
        base_url=AGENT_ROUTER_URL,
        api_key=AGENT_ROUTER_KEY,
        temperature=0.1,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        callbacks=callbacks,
    )

    # Define tools for implementation
    tools = [
        # Codebase analysis tools
        load_codebase_tool,
        index_codebase_tool,
        search_similar_code_tool,
        # Virtual FS sync tools (CRITICAL for Git workflow)
        sync_virtual_to_disk_tool,
        list_virtual_files_tool,
        # Stack detection & boilerplate
        detect_stack_tool,
        retrieve_boilerplate_tool,
        # Git operations
        create_feature_branch_tool,
        commit_changes_tool,
        create_pull_request_tool,
        # Code generation & strategy
        select_integration_strategy_tool,
        generate_code_tool,
        # Review & feedback
        collect_feedback_tool,
        refine_code_tool,
    ]

    # Define subagents for specialized tasks
    subagents = [
        code_generator_subagent,
    ]

    # Create the deep agent
    # DeepAgents will automatically add:
    # - PlanningMiddleware with write_todos tool
    # - FilesystemMiddleware for mock file operations
    # - SubAgentMiddleware for spawning subagents
    # - SummarizationMiddleware for token management
    agent = create_deep_agent(
        tools=tools,
        instructions=instructions,
        subagents=subagents,
        model=llm,
        checkpointer=False,
    ).with_config(
        {
            "recursion_limit": config.get("recursion_limit", 500),
            "model_name": model_name,
        }
    )

    return agent


async def run_developer(
    user_request: str,
    working_directory: str = ".",
    project_type: str = "existing",
    enable_pgvector: bool = True,
    boilerplate_templates_path: str = None,
    model_name: str = "gpt-4o-mini",
    session_id: str = None,
    user_id: str = None,
    **config,
) -> Dict[str, Any]:
    """
    Run the implementor agent with a user request and Langfuse tracing.

    This is the main entry point for using the implementor.

    Args:
        user_request: The user's implementation request
        working_directory: Working directory for the agent
        project_type: "new" for new projects, "existing" for existing codebases
        enable_pgvector: Whether to enable pgvector indexing
        boilerplate_templates_path: Path to boilerplate templates
        model_name: LLM model to use
        session_id: Optional session ID for Langfuse tracing
        user_id: Optional user ID for Langfuse tracing
        **config: Additional configuration

    Returns:
        Final state with implementation results

    Example:
        result = await run_implementor(
            user_request="Add user authentication with JWT",
            working_directory="./src",
            project_type="existing",
            session_id="dev-session-123"
        )
        print(result['todos'])  # See implementation progress
    """
    import time
    from pathlib import Path

    start_time = time.time()

    # Normalize working_directory to absolute path
    working_directory = str(Path(working_directory).resolve())
    print(f"🔧 Normalized working directory: {working_directory}")

    # Generate session_id if not provided
    if not session_id:
        import uuid

        session_id = f"dev-{uuid.uuid4().hex[:8]}"

    # Create the agent with tracing enabled
    agent = create_developer_agent(
        working_directory=working_directory,
        project_type=project_type,
        enable_pgvector=enable_pgvector,
        boilerplate_templates_path=boilerplate_templates_path,
        model_name=model_name,
        session_id=session_id,
        user_id=user_id,
        **config,
    )

    # Create initial state
    initial_state = {
        "messages": [{"role": "user", "content": user_request}],
        "working_directory": working_directory,
        "project_type": project_type,
        "user_request": user_request,
        "enable_pgvector": enable_pgvector,
        "boilerplate_templates_path": boilerplate_templates_path,
        "implementation_status": "started",
        "generated_files": [],
        "commit_history": [],
    }

    # Log initial state to Langfuse
    if LANGFUSE_AVAILABLE:
        log_agent_state(initial_state, "initialization")
        print(f"📊 Langfuse tracing: Session {session_id}")

    # Run the agent with tracing
    # DeepAgents will automatically handle the workflow:
    # 1. Use write_todos to create implementation plan
    # 2. Execute each todo task
    # 3. Update todo status as tasks complete
    # 4. Handle user feedback and refinements

    try:
        # Wrap agent execution in a trace span
        with trace_span(
            name="developer_agent_execution",
            metadata={
                "session_id": session_id,
                "user_id": user_id,
                "user_request": user_request,
                "working_directory": working_directory,
                "project_type": project_type,
                "model_name": model_name,
            },
            input_data={"user_request": user_request, "initial_state": initial_state},
        ) as span:
            print("🚀 Starting developer agent execution...")
            result = await agent.ainvoke(initial_state)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Log final state to Langfuse
            if LANGFUSE_AVAILABLE:
                log_agent_state(result, "completion")

                # Update span with output
                if span:
                    span.end(
                        output={
                            "implementation_status": result.get("implementation_status"),
                            "generated_files_count": len(result.get("generated_files", [])),
                            "commit_count": len(result.get("commit_history", [])),
                            "todos_completed": sum(
                                1 for t in result.get("todos", []) if t.get("status") == "completed"
                            ),
                            "execution_time_seconds": execution_time,
                        }
                    )

            print(f"✅ Developer agent execution completed in {execution_time:.2f}s")

            return result

    except Exception as e:
        print(f"❌ Developer agent execution failed: {e}")

        # Log error to Langfuse
        if LANGFUSE_AVAILABLE:
            with trace_span(
                name="agent_error",
                metadata={
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            ):
                pass

        raise

    finally:
        # Flush Langfuse traces
        if LANGFUSE_AVAILABLE:
            flush_langfuse()


# Example usage for testing
if __name__ == "__main__":
    import asyncio

    async def main():
        result = await run_developer(
            user_request="Add user profile to the FastAPI application",
            working_directory=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
            project_type="existing",
            enable_pgvector=True,
        )

        print("=" * 80)
        print("Implementation Results:")
        print("=" * 80)
        print(f"Status: {result.get('implementation_status', 'Unknown')}")
        print(f"Generated Files: {len(result.get('generated_files', []))}")
        print(f"Commits: {len(result.get('commit_history', []))}")

        if "todos" in result:
            print("\nTodos:")
            for i, todo in enumerate(result["todos"], 1):
                status = todo.get("status", "unknown")
                content = todo.get("content", "No content")
                print(f"{i}. [{status}] {content}")

    asyncio.run(main())
