"""
Sprint Task Executor

Orchestrator that reads sprint backlog from Product Owner Agent output
and automatically executes Development/Infrastructure tasks using Developer Agent.

This module bridges the gap between Product Owner Agent (planning) and
Developer Agent (implementation) by:
1. Reading sprint.json and backlog.json files
2. Filtering tasks by task_type (Development/Infrastructure)
3. Resolving task dependencies
4. Executing Developer Agent for each task
5. Tracking progress with Langfuse tracing

Usage:
    from app.orchestrators import execute_sprint

    results = await execute_sprint(
        sprint_id="sprint-1",
        working_directory="./target_project"
    )
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime


def _import_run_developer():
    """
    Lazy import of run_developer to avoid circular imports and module loading issues.

    This function imports run_developer only when needed, allowing the module
    to be imported without requiring all dependencies to be available.
    """
    try:
        # Try relative import first (when used as package)
        # Now we're in agents.developer.orchestrators, so agent is one level up
        from ..agent import run_developer

        return run_developer
    except ImportError:
        # Fall back to absolute import (when used as script)
        import sys
        from pathlib import Path

        # Add app directory to path
        app_dir = Path(__file__).parent.parent.parent.parent
        if str(app_dir) not in sys.path:
            sys.path.insert(0, str(app_dir))

        from agents.developer.agent import run_developer

        return run_developer


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
        # Current file: app/agents/developer/orchestrators/sprint_executor.py
        # Need to go up to app/ then to agents/product_owner/
        if backlog_path is None:
            backlog_path = str(
                Path(__file__).parent.parent.parent.parent
                / "agents"
                / "product_owner"
                / "backlog.json"
            )
        if sprint_path is None:
            sprint_path = str(
                Path(__file__).parent.parent.parent.parent
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

    def load_backlog(self) -> List[Dict[str, Any]]:
        """Load backlog items from backlog.json."""
        with open(self.backlog_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_sprint(self, sprint_id: str) -> Dict[str, Any]:
        """
        Load sprint data from sprint.json.

        Args:
            sprint_id: Sprint ID to load (e.g., "sprint-1")

        Returns:
            Sprint data dictionary

        Raises:
            ValueError: If sprint not found
        """
        with open(self.sprint_path, "r", encoding="utf-8") as f:
            sprints = json.load(f)

        # Find sprint by ID
        sprint = next((s for s in sprints if s["sprint_id"] == sprint_id), None)
        if not sprint:
            raise ValueError(f"Sprint not found: {sprint_id}")

        return sprint

    def filter_development_tasks(
        self,
        sprint_data: Dict[str, Any],
        backlog_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
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
        tasks: List[Dict[str, Any]],
        all_backlog_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
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
        graph: Dict[str, Set[str]] = {task_id: set() for task_id in task_ids}
        in_degree: Dict[str, int] = {task_id: 0 for task_id in task_ids}

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

    def format_task_as_request(self, task: Dict[str, Any]) -> str:
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
        task: Dict[str, Any],
        sprint_id: str,
        task_index: int,
        total_tasks: int,
    ) -> Dict[str, Any]:
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
            # Lazy import to avoid module loading issues
            run_developer = _import_run_developer()

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
    ) -> Dict[str, Any]:
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


# Convenience functions for direct usage


async def execute_sprint(
    sprint_id: str,
    working_directory: str = ".",
    backlog_path: str = None,
    sprint_path: str = None,
    model_name: str = "gpt-4o-mini",
    enable_pgvector: bool = True,
    continue_on_error: bool = True,
) -> Dict[str, Any]:
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
) -> List[Dict[str, Any]]:
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


def format_task_as_request(task: Dict[str, Any]) -> str:
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
