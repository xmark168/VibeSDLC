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

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent

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
        flush_langfuse,
        get_callback_handler,
        log_agent_state,
        trace_span,
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
    from agents.developer.implementor.subagents import code_generator_subagent
    from agents.developer.implementor.tools import (
        collect_feedback_tool,
        commit_changes_tool,
        create_feature_branch_tool,
        create_pull_request_tool,
        detect_stack_tool,
        generate_code_tool,
        index_codebase_tool,
        list_virtual_files_tool,
        load_codebase_tool,
        refine_code_tool,
        retrieve_boilerplate_tool,
        search_similar_code_tool,
        select_integration_strategy_tool,
        sync_virtual_to_disk_tool,
    )
    from instructions import get_implementor_instructions
else:
    # Package import - use relative imports
    from agents.developer.implementor.subagents import code_generator_subagent
    from agents.developer.implementor.tools import (
        collect_feedback_tool,
        commit_changes_tool,
        create_feature_branch_tool,
        create_pull_request_tool,
        detect_stack_tool,
        generate_code_tool,
        index_codebase_tool,
        list_virtual_files_tool,
        load_codebase_tool,
        refine_code_tool,
        retrieve_boilerplate_tool,
        search_similar_code_tool,
        select_integration_strategy_tool,
        sync_virtual_to_disk_tool,
    )

    from .instructions import get_implementor_instructions


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
) -> dict[str, Any]:
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
                            "implementation_status": result.get(
                                "implementation_status"
                            ),
                            "generated_files_count": len(
                                result.get("generated_files", [])
                            ),
                            "commit_count": len(result.get("commit_history", [])),
                            "todos_completed": sum(
                                1
                                for t in result.get("todos", [])
                                if t.get("status") == "completed"
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


# ============================================================================
# Sprint Task Executor
# ============================================================================
# Orchestrator that reads sprint backlog from Product Owner Agent output
# and automatically executes Development/Infrastructure tasks using Developer Agent.
#
# This bridges the gap between Product Owner Agent (planning) and
# Developer Agent (implementation) by:
# 1. Reading sprint.json and backlog.json files
# 2. Filtering tasks by task_type (Development/Infrastructure)
# 3. Resolving task dependencies
# 4. Executing Developer Agent for each task
# 5. Tracking progress with Langfuse tracing
# ============================================================================


class SprintTaskExecutor:
    """
    Orchestrator for executing sprint tasks with Developer Agent.

    Reads Product Owner Agent output (sprint.json + backlog.json) and
    automatically executes Development/Infrastructure tasks.
    """

    def __init__(
        self,
        backlog_path: str = None,
        sprint_path: str = None,
        working_directory: str = ".",
        model_name: str = "gpt-4o-mini",
        enable_pgvector: bool = True,
    ):
        """
        Initialize Sprint Task Executor.

        Args:
            backlog_path: Path to backlog.json (default: auto-detect)
            sprint_path: Path to sprint.json (default: auto-detect)
            working_directory: Working directory for Developer Agent
            model_name: LLM model to use
            enable_pgvector: Enable pgvector indexing
        """
        # Auto-detect paths if not provided
        # Current file: app/agents/developer/agent.py
        # Need to go up to app/ then to agents/product_owner/
        if backlog_path is None:
            backlog_path = str(
                Path(__file__).parent.parent.parent
                / "agents"
                / "product_owner"
                / "backlog.json"
            )
        if sprint_path is None:
            sprint_path = str(
                Path(__file__).parent.parent.parent
                / "agents"
                / "product_owner"
                / "sprint.json"
            )

        self.backlog_path = Path(backlog_path)
        self.sprint_path = Path(sprint_path)
        self.working_directory = working_directory
        self.model_name = model_name
        self.enable_pgvector = enable_pgvector

        # Validate paths
        if not self.backlog_path.exists():
            raise FileNotFoundError(f"Backlog file not found: {self.backlog_path}")
        if not self.sprint_path.exists():
            raise FileNotFoundError(f"Sprint file not found: {self.sprint_path}")

    def load_backlog(self) -> list[dict[str, Any]]:
        """Load backlog items from backlog.json."""
        with open(self.backlog_path, encoding="utf-8") as f:
            return json.load(f)

    def load_sprint(self, sprint_id: str) -> dict[str, Any]:
        """
        Load sprint data from sprint.json.

        Args:
            sprint_id: Sprint ID to load (e.g., "sprint-1")

        Returns:
            Sprint data dictionary

        Raises:
            ValueError: If sprint not found
        """
        with open(self.sprint_path, encoding="utf-8") as f:
            sprints = json.load(f)

        # Find sprint by ID
        sprint = next((s for s in sprints if s["sprint_id"] == sprint_id), None)
        if not sprint:
            raise ValueError(f"Sprint not found: {sprint_id}")

        return sprint

    def filter_development_tasks(
        self,
        sprint_data: dict[str, Any],
        backlog_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Filter tasks that should be executed by Developer Agent.

        Filters for:
        - Items assigned to the sprint
        - task_type in ["Development", "Infrastructure"]
        - Type is "Task" or "Sub-task"

        Args:
            sprint_data: Sprint data with assigned_items
            backlog_items: All backlog items

        Returns:
            List of filtered tasks
        """
        assigned_item_ids = set(sprint_data["assigned_items"])

        # Filter items in sprint
        sprint_items = [
            item for item in backlog_items if item["id"] in assigned_item_ids
        ]

        # Filter by task_type
        dev_tasks = [
            item
            for item in sprint_items
            if item.get("task_type") in ["Development", "Infrastructure"]
            and item.get("type") in ["Task", "Sub-task"]
        ]

        return dev_tasks

    def resolve_dependencies(
        self,
        tasks: list[dict[str, Any]],
        all_backlog_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Sort tasks by dependencies using topological sort.

        Tasks with dependencies will be placed after their dependencies.
        If a dependency is not in the task list (e.g., Testing task),
        it will be ignored.

        Args:
            tasks: List of tasks to sort
            all_backlog_items: All backlog items for dependency lookup

        Returns:
            Sorted list of tasks
        """
        task_ids = {task["id"] for task in tasks}
        task_map = {task["id"]: task for task in tasks}

        # Build dependency graph (only for tasks in our list)
        graph: dict[str, set[str]] = {task_id: set() for task_id in task_ids}
        in_degree: dict[str, int] = dict.fromkeys(task_ids, 0)

        for task in tasks:
            task_id = task["id"]
            dependencies = task.get("dependencies", [])

            for dep_id in dependencies:
                # Only consider dependencies that are in our task list
                if dep_id in task_ids:
                    graph[dep_id].add(task_id)
                    in_degree[task_id] += 1

        # Topological sort using Kahn's algorithm
        queue = [task_id for task_id in task_ids if in_degree[task_id] == 0]
        sorted_tasks = []

        while queue:
            # Sort queue for deterministic order
            queue.sort()
            task_id = queue.pop(0)
            sorted_tasks.append(task_map[task_id])

            # Reduce in-degree for dependent tasks
            for dependent_id in graph[task_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check for circular dependencies
        if len(sorted_tasks) != len(tasks):
            print("⚠️  Warning: Circular dependencies detected. Using original order.")
            return tasks

        return sorted_tasks

    def format_task_as_request(self, task: dict[str, Any]) -> str:
        """
        Format a backlog task as a user_request for Developer Agent.

        Includes:
        - Task title and description
        - Acceptance criteria
        - Labels for context

        Args:
            task: Backlog task item

        Returns:
            Formatted user_request string
        """
        request_parts = []

        # Title
        request_parts.append(f"# {task['title']}")
        request_parts.append("")

        # Description
        if task.get("description"):
            request_parts.append("## Description")
            request_parts.append(task["description"])
            request_parts.append("")

        # Acceptance Criteria
        if task.get("acceptance_criteria"):
            request_parts.append("## Acceptance Criteria")
            for i, criterion in enumerate(task["acceptance_criteria"], 1):
                request_parts.append(f"{i}. {criterion}")
            request_parts.append("")

        # Labels for context
        if task.get("labels"):
            request_parts.append(f"## Labels: {', '.join(task['labels'])}")
            request_parts.append("")

        # Task metadata
        request_parts.append("## Task Info")
        request_parts.append(f"- Task ID: {task['id']}")
        request_parts.append(f"- Type: {task['type']}")
        request_parts.append(f"- Task Type: {task.get('task_type', 'N/A')}")
        if task.get("estimate_value"):
            request_parts.append(f"- Estimate: {task['estimate_value']} hours")

        return "\n".join(request_parts)

    async def execute_task(
        self,
        task: dict[str, Any],
        sprint_id: str,
        task_index: int,
        total_tasks: int,
    ) -> dict[str, Any]:
        """
        Execute a single task with Developer Agent.

        Args:
            task: Backlog task to execute
            sprint_id: Sprint ID for tracing
            task_index: Current task index (1-based)
            total_tasks: Total number of tasks

        Returns:
            Execution result from Developer Agent
        """
        task_id = task["id"]

        print("=" * 80)
        print(f"📋 Task {task_index}/{total_tasks}: {task['title']}")
        print(f"   ID: {task_id}")
        print(f"   Type: {task.get('task_type', 'N/A')}")
        print("=" * 80)

        # Format task as user_request
        user_request = self.format_task_as_request(task)

        # Generate session ID for Langfuse tracing
        session_id = f"sprint-{sprint_id}-{task_id}"
        user_id = "sprint-executor"

        # Execute Developer Agent
        try:
            result = await run_developer(
                user_request=user_request,
                working_directory=self.working_directory,
                project_type="existing",
                enable_pgvector=self.enable_pgvector,
                model_name=self.model_name,
                session_id=session_id,
                user_id=user_id,
            )

            print(f"✅ Task {task_id} completed successfully")
            return {
                "task_id": task_id,
                "status": "success",
                "result": result,
            }

        except Exception as e:
            print(f"❌ Task {task_id} failed: {str(e)}")
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
            }

    async def execute_sprint(
        self,
        sprint_id: str,
        continue_on_error: bool = True,
    ) -> dict[str, Any]:
        """
        Execute all Development/Infrastructure tasks in a sprint.

        Main orchestration method that:
        1. Loads sprint and backlog data
        2. Filters Development/Infrastructure tasks
        3. Resolves dependencies
        4. Executes each task with Developer Agent
        5. Tracks progress and results

        Args:
            sprint_id: Sprint ID to execute (e.g., "sprint-1")
            continue_on_error: Continue executing tasks if one fails

        Returns:
            Dictionary with execution summary and results
        """
        start_time = datetime.now()

        print("🚀 Sprint Task Executor Started")
        print(f"   Sprint ID: {sprint_id}")
        print(f"   Working Directory: {self.working_directory}")
        print(f"   Model: {self.model_name}")
        print("=" * 80)

        # Load data
        print("📂 Loading sprint and backlog data...")
        sprint_data = self.load_sprint(sprint_id)
        backlog_items = self.load_backlog()

        print(f"   Sprint: {sprint_data['sprint_goal']}")
        print(f"   Assigned Items: {len(sprint_data['assigned_items'])}")
        print(f"   Total Backlog Items: {len(backlog_items)}")

        # Filter Development/Infrastructure tasks
        print("\n🔍 Filtering Development/Infrastructure tasks...")
        dev_tasks = self.filter_development_tasks(sprint_data, backlog_items)
        print(f"   Found {len(dev_tasks)} tasks to execute")

        if not dev_tasks:
            print("⚠️  No Development/Infrastructure tasks found in sprint")
            return {
                "sprint_id": sprint_id,
                "status": "no_tasks",
                "tasks_executed": 0,
                "tasks_succeeded": 0,
                "tasks_failed": 0,
                "results": [],
            }

        # Resolve dependencies
        print("\n🔗 Resolving task dependencies...")
        sorted_tasks = self.resolve_dependencies(dev_tasks, backlog_items)

        print("   Execution order:")
        for i, task in enumerate(sorted_tasks, 1):
            deps = task.get("dependencies", [])
            deps_str = f" (depends on: {', '.join(deps)})" if deps else ""
            print(f"   {i}. {task['id']}: {task['title']}{deps_str}")

        # Execute tasks
        print("\n🏃 Executing tasks...")
        results = []

        for i, task in enumerate(sorted_tasks, 1):
            result = await self.execute_task(
                task=task,
                sprint_id=sprint_id,
                task_index=i,
                total_tasks=len(sorted_tasks),
            )
            results.append(result)

            # Stop on error if configured
            if result["status"] == "failed" and not continue_on_error:
                print(f"\n⛔ Stopping execution due to task failure: {task['id']}")
                break

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        succeeded = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")

        print("\n" + "=" * 80)
        print("📊 Sprint Execution Summary")
        print("=" * 80)
        print(f"   Sprint ID: {sprint_id}")
        print(f"   Total Tasks: {len(sorted_tasks)}")
        print(f"   Executed: {len(results)}")
        print(f"   ✅ Succeeded: {succeeded}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏱️  Duration: {duration:.2f}s")
        print("=" * 80)

        return {
            "sprint_id": sprint_id,
            "status": "completed" if failed == 0 else "partial",
            "tasks_total": len(sorted_tasks),
            "tasks_executed": len(results),
            "tasks_succeeded": succeeded,
            "tasks_failed": failed,
            "duration_seconds": duration,
            "results": results,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }


# ============================================================================
# Sprint Task Executor - Convenience Functions
# ============================================================================


async def execute_sprint(
    sprint_id: str,
    working_directory: str = ".",
    backlog_path: str = None,
    sprint_path: str = None,
    model_name: str = "gpt-4o-mini",
    enable_pgvector: bool = True,
    continue_on_error: bool = True,
) -> dict[str, Any]:
    """
    Execute all Development/Infrastructure tasks in a sprint.

    Convenience function that creates a SprintTaskExecutor and runs it.

    Args:
        sprint_id: Sprint ID to execute (e.g., "sprint-1")
        working_directory: Working directory for Developer Agent
        backlog_path: Path to backlog.json (default: auto-detect)
        sprint_path: Path to sprint.json (default: auto-detect)
        model_name: LLM model to use
        enable_pgvector: Enable pgvector indexing
        continue_on_error: Continue executing tasks if one fails

    Returns:
        Dictionary with execution summary and results

    Example:
        results = await execute_sprint(
            sprint_id="sprint-1",
            working_directory="./target_project"
        )
    """
    executor = SprintTaskExecutor(
        backlog_path=backlog_path,
        sprint_path=sprint_path,
        working_directory=working_directory,
        model_name=model_name,
        enable_pgvector=enable_pgvector,
    )

    return await executor.execute_sprint(
        sprint_id=sprint_id,
        continue_on_error=continue_on_error,
    )


def filter_development_tasks(
    sprint_id: str,
    backlog_path: str = None,
    sprint_path: str = None,
) -> list[dict[str, Any]]:
    """
    Filter Development/Infrastructure tasks from a sprint.

    Utility function to preview which tasks would be executed.

    Args:
        sprint_id: Sprint ID
        backlog_path: Path to backlog.json (default: auto-detect)
        sprint_path: Path to sprint.json (default: auto-detect)

    Returns:
        List of filtered tasks

    Example:
        tasks = filter_development_tasks("sprint-1")
        for task in tasks:
            print(f"{task['id']}: {task['title']}")
    """
    executor = SprintTaskExecutor(
        backlog_path=backlog_path,
        sprint_path=sprint_path,
    )

    sprint_data = executor.load_sprint(sprint_id)
    backlog_items = executor.load_backlog()

    return executor.filter_development_tasks(sprint_data, backlog_items)


def format_task_as_request(task: dict[str, Any]) -> str:
    """
    Format a backlog task as a user_request for Developer Agent.

    Utility function to preview how a task will be formatted.

    Args:
        task: Backlog task item

    Returns:
        Formatted user_request string

    Example:
        task = {"id": "TASK-001", "title": "Add feature", ...}
        request = format_task_as_request(task)
        print(request)
    """
    executor = SprintTaskExecutor()
    return executor.format_task_as_request(task)


# ============================================================================
# Main Execution - Sprint Task Executor
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def run_sprint_executor():
        """Run the Sprint Task Executor"""
        try:
            # Khởi tạo executor
            executor = SprintTaskExecutor(
                working_directory=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
                model_name="gpt-4o-mini",
                enable_pgvector=True,
            )

            # Thực thi sprint (thay "sprint-1" bằng sprint ID thực tế của bạn)
            sprint_id = "sprint-1"  # Thay đổi này thành sprint ID thực tế

            print("🚀 Starting Sprint Task Executor...")
            results = await executor.execute_sprint(sprint_id)

            # Hiển thị kết quả
            print("\n" + "=" * 80)
            print("🎯 FINAL RESULTS")
            print("=" * 80)
            print(f"Sprint ID: {results['sprint_id']}")
            print(f"Status: {results['status']}")
            print(
                f"Tasks Executed: {results['tasks_executed']}/{results['tasks_total']}"
            )
            print(f"Succeeded: {results['tasks_succeeded']}")
            print(f"Failed: {results['tasks_failed']}")
            print(f"Duration: {results['duration_seconds']:.2f}s")

            # Hiển thị chi tiết từng task
            print("\n📋 Task Details:")
            for i, result in enumerate(results["results"], 1):
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"{i}. {status_icon} {result['task_id']}: {result['status']}")

        except Exception as e:
            print(f"❌ Sprint execution failed: {e}")
            import traceback

            traceback.print_exc()

    # Chạy executor
    asyncio.run(run_sprint_executor())
