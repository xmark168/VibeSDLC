"""Task and Plan models for MetaGPT-style planning system.

This module provides task dependency management with topological sorting,
allowing agents to plan and execute complex multi-step workflows.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4


@dataclass
class Task:
    """Represents a single task in a plan with dependencies."""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    instruction: str = ""
    dependent_task_ids: List[str] = field(default_factory=list)

    # Task metadata
    task_type: str = "generic"  # generic, code, test, review, etc.
    assignee: Optional[str] = None  # Which agent/role handles this
    priority: int = 0

    # Execution tracking
    is_finished: bool = False
    is_success: bool = False

    # Results
    code: str = ""  # For code generation tasks
    result: str = ""  # Task output

    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.task_id)


@dataclass
class Plan:
    """Represents a plan with tasks and dependency management.

    Inspired by MetaGPT's Plan class with topological sorting for
    dependency-based execution ordering.
    """

    goal: str = ""
    context: str = ""
    tasks: List[Task] = field(default_factory=list)
    task_map: Dict[str, Task] = field(default_factory=dict)
    current_task_id: Optional[str] = None

    # Plan metadata
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize task map and sort tasks by dependencies."""
        if self.tasks and not self.task_map:
            self._build_task_map()
            self._sort_tasks_by_dependencies()

    def _build_task_map(self):
        """Build task_id -> Task mapping."""
        self.task_map = {task.task_id: task for task in self.tasks}

    def _sort_tasks_by_dependencies(self):
        """Sort tasks using topological sort to respect dependencies.

        Uses Kahn's algorithm for topological sorting.
        """
        if not self.tasks:
            return

        # Build adjacency list and in-degree map
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize all tasks with 0 in-degree
        for task in self.tasks:
            in_degree[task.task_id] = 0

        # Build graph
        for task in self.tasks:
            for dep_id in task.dependent_task_ids:
                if dep_id in self.task_map:
                    graph[dep_id].append(task.task_id)
                    in_degree[task.task_id] += 1

        # Find all tasks with no dependencies (in-degree = 0)
        queue = deque([
            task_id for task_id in self.task_map.keys()
            if in_degree[task_id] == 0
        ])

        sorted_task_ids = []

        while queue:
            current_id = queue.popleft()
            sorted_task_ids.append(current_id)

            # Reduce in-degree for dependent tasks
            for neighbor_id in graph[current_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        # Check for circular dependencies
        if len(sorted_task_ids) != len(self.tasks):
            raise ValueError("Circular dependency detected in task plan")

        # Reorder tasks based on topological sort
        self.tasks = [self.task_map[task_id] for task_id in sorted_task_ids]

        # Set current task to first unfinished task
        self._update_current_task()

    def add_task(self, task: Task):
        """Add a single task to the plan.

        Args:
            task: Task to add
        """
        self.tasks.append(task)
        self.task_map[task.task_id] = task
        self._sort_tasks_by_dependencies()

    def add_tasks(self, new_tasks: List[Task]):
        """Add multiple tasks to the plan.

        Merges new tasks with existing ones, maintaining common prefix
        and resolving dependencies.

        Args:
            new_tasks: List of tasks to add
        """
        if not new_tasks:
            return

        # Find common prefix between existing and new tasks
        common_prefix_len = 0
        for i, (old_task, new_task) in enumerate(zip(self.tasks, new_tasks)):
            if old_task.instruction == new_task.instruction:
                common_prefix_len = i + 1
            else:
                break

        # Keep common prefix, add new tasks
        self.tasks = self.tasks[:common_prefix_len] + new_tasks[common_prefix_len:]

        # Rebuild task map
        self._build_task_map()
        self._sort_tasks_by_dependencies()

    def remove_task(self, task_id: str):
        """Remove a task from the plan.

        Args:
            task_id: ID of task to remove
        """
        if task_id not in self.task_map:
            return

        # Remove from tasks list
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

        # Remove from task map
        del self.task_map[task_id]

        # Remove from other tasks' dependencies
        for task in self.tasks:
            if task_id in task.dependent_task_ids:
                task.dependent_task_ids.remove(task_id)

        self._update_current_task()

    @property
    def current_task(self) -> Optional[Task]:
        """Get the current task being executed.

        Returns:
            Current Task or None if no current task
        """
        if not self.current_task_id:
            return None
        return self.task_map.get(self.current_task_id)

    def _update_current_task(self):
        """Update current_task_id to the next unfinished task."""
        for task in self.tasks:
            if not task.is_finished:
                self.current_task_id = task.task_id
                return
        # All tasks finished
        self.current_task_id = None

    def finish_current_task(self, success: bool = True, result: str = ""):
        """Mark current task as finished and move to next.

        Args:
            success: Whether task completed successfully
            result: Task result/output
        """
        if not self.current_task:
            return

        self.current_task.is_finished = True
        self.current_task.is_success = success
        self.current_task.result = result

        self._update_current_task()

    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks whose dependencies are satisfied.

        Returns:
            List of tasks ready to execute
        """
        ready = []
        for task in self.tasks:
            if task.is_finished:
                continue

            # Check if all dependencies are finished
            deps_finished = all(
                self.task_map.get(dep_id, Task()).is_finished
                for dep_id in task.dependent_task_ids
            )

            if deps_finished:
                ready.append(task)

        return ready

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        return self.task_map.get(task_id)

    def get_finished_tasks(self) -> List[Task]:
        """Get all finished tasks.

        Returns:
            List of finished tasks
        """
        return [task for task in self.tasks if task.is_finished]

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending (unfinished) tasks.

        Returns:
            List of pending tasks
        """
        return [task for task in self.tasks if not task.is_finished]

    @property
    def is_completed(self) -> bool:
        """Check if all tasks in the plan are completed.

        Returns:
            True if all tasks finished, False otherwise
        """
        return all(task.is_finished for task in self.tasks)

    @property
    def is_successful(self) -> bool:
        """Check if all tasks completed successfully.

        Returns:
            True if all tasks finished and succeeded
        """
        return all(task.is_finished and task.is_success for task in self.tasks)

    @property
    def progress(self) -> float:
        """Calculate plan completion progress.

        Returns:
            Progress as percentage (0.0 to 1.0)
        """
        if not self.tasks:
            return 1.0
        finished = len([t for t in self.tasks if t.is_finished])
        return finished / len(self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize plan to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "context": self.context,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "instruction": task.instruction,
                    "dependent_task_ids": task.dependent_task_ids,
                    "task_type": task.task_type,
                    "assignee": task.assignee,
                    "priority": task.priority,
                    "is_finished": task.is_finished,
                    "is_success": task.is_success,
                    "result": task.result,
                    "code": task.code,
                    "context": task.context,
                    "metadata": task.metadata,
                }
                for task in self.tasks
            ],
            "current_task_id": self.current_task_id,
            "created_by": self.created_by,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        """Deserialize plan from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Plan instance
        """
        tasks = [
            Task(
                task_id=t["task_id"],
                instruction=t["instruction"],
                dependent_task_ids=t.get("dependent_task_ids", []),
                task_type=t.get("task_type", "generic"),
                assignee=t.get("assignee"),
                priority=t.get("priority", 0),
                is_finished=t.get("is_finished", False),
                is_success=t.get("is_success", False),
                result=t.get("result", ""),
                code=t.get("code", ""),
                context=t.get("context", {}),
                metadata=t.get("metadata", {}),
            )
            for t in data.get("tasks", [])
        ]

        plan = cls(
            plan_id=data.get("plan_id", str(uuid4())),
            goal=data.get("goal", ""),
            context=data.get("context", ""),
            tasks=tasks,
            current_task_id=data.get("current_task_id"),
            created_by=data.get("created_by"),
            metadata=data.get("metadata", {}),
        )

        return plan

    def __repr__(self) -> str:
        finished = len(self.get_finished_tasks())
        total = len(self.tasks)
        return f"Plan(goal='{self.goal}', progress={finished}/{total}, current={self.current_task_id})"
