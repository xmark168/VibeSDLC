"""Planner for dynamic task planning and execution.

This module provides a Planner that can create plans, update them dynamically,
and manage task execution with LLM assistance.
"""

import logging
from typing import Any, Dict, List, Optional

from app.agents.base.action import Action
from app.agents.base.message import Memory, Message
from app.agents.base.plan import Plan, Task

logger = logging.getLogger(__name__)


class Planner:
    """Dynamic planner for creating and managing task execution plans.

    Inspired by MetaGPT's Planner with support for:
    - Plan generation from goals
    - Dynamic plan updates based on feedback
    - Task dependency management
    - Working memory for task context
    """

    def __init__(
        self,
        goal: str = "",
        auto_run: bool = False,
        use_llm_for_planning: bool = True,
    ):
        """Initialize Planner.

        Args:
            goal: Overall goal for the plan
            auto_run: Whether to automatically execute tasks
            use_llm_for_planning: Whether to use LLM for plan generation
        """
        self.plan = Plan(goal=goal)
        self.working_memory = Memory()  # Task-specific memory
        self.auto_run = auto_run
        self.use_llm_for_planning = use_llm_for_planning

        # Planning prompts (can be customized)
        self.planning_prompt_template = """
Based on the goal and context, create a detailed plan with tasks.

Goal: {goal}

Context: {context}

Create a plan with the following format:
- Each task should have a clear instruction
- Specify dependencies between tasks (if any)
- Assign task types (code, test, review, etc.)
- Assign to appropriate roles/agents

Return a JSON array of tasks with this structure:
[
  {{
    "instruction": "Clear task description",
    "task_type": "code|test|review|design|etc",
    "assignee": "Developer|Tester|Architect|etc",
    "dependent_task_ids": [],
    "priority": 0
  }}
]
"""

    def set_plan(self, plan: Plan):
        """Set the current plan.

        Args:
            plan: Plan to set
        """
        self.plan = plan

    async def create_plan(
        self,
        goal: str,
        context: str = "",
        max_tasks: int = 10,
        llm_action: Optional[Action] = None,
    ) -> Plan:
        """Create a new plan for the given goal.

        Args:
            goal: Goal to achieve
            context: Additional context for planning
            max_tasks: Maximum number of tasks to create
            llm_action: Optional LLM action for AI-assisted planning

        Returns:
            Created Plan
        """
        self.plan = Plan(goal=goal, context=context)

        if self.use_llm_for_planning and llm_action:
            # Use LLM to generate plan
            tasks = await self._generate_plan_with_llm(
                goal=goal,
                context=context,
                max_tasks=max_tasks,
                llm_action=llm_action,
            )
            self.plan.add_tasks(tasks)
        else:
            # Manual planning or pre-defined task templates
            logger.info("LLM planning not enabled, plan must be set manually")

        logger.info(f"Created plan with {len(self.plan.tasks)} tasks for goal: {goal}")
        return self.plan

    async def _generate_plan_with_llm(
        self,
        goal: str,
        context: str,
        max_tasks: int,
        llm_action: Action,
    ) -> List[Task]:
        """Generate plan using LLM.

        Args:
            goal: Goal to achieve
            context: Planning context
            max_tasks: Maximum tasks to generate
            llm_action: LLM action to use

        Returns:
            List of generated tasks
        """
        import json

        # Format prompt
        prompt = self.planning_prompt_template.format(
            goal=goal,
            context=context,
        )

        # Call LLM (assuming llm_action has a run method)
        try:
            result = await llm_action.run(prompt)

            # Parse JSON response
            if hasattr(result, 'content'):
                content = result.content
            else:
                content = str(result)

            # Extract JSON from response
            tasks_data = self._extract_json_from_response(content)

            # Create Task objects
            tasks = []
            for i, task_data in enumerate(tasks_data[:max_tasks]):
                task = Task(
                    instruction=task_data.get("instruction", ""),
                    task_type=task_data.get("task_type", "generic"),
                    assignee=task_data.get("assignee"),
                    dependent_task_ids=task_data.get("dependent_task_ids", []),
                    priority=task_data.get("priority", i),
                )
                tasks.append(task)

            return tasks

        except Exception as e:
            logger.error(f"Failed to generate plan with LLM: {e}")
            return []

    def _extract_json_from_response(self, response: str) -> List[Dict[str, Any]]:
        """Extract JSON array from LLM response.

        Args:
            response: LLM response text

        Returns:
            Parsed JSON array
        """
        import json
        import re

        # Try to find JSON array in response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # If not found, return empty list
        logger.warning("Could not extract JSON from LLM response")
        return []

    async def update_plan(
        self,
        new_goal: Optional[str] = None,
        new_tasks: Optional[List[Task]] = None,
        llm_action: Optional[Action] = None,
    ):
        """Update the current plan with new goal or tasks.

        Args:
            new_goal: Optional new goal
            new_tasks: Optional new tasks to add
            llm_action: Optional LLM action for replanning
        """
        if new_goal:
            self.plan.goal = new_goal

        if new_tasks:
            self.plan.add_tasks(new_tasks)
        elif self.use_llm_for_planning and llm_action and new_goal:
            # Regenerate plan with new goal
            tasks = await self._generate_plan_with_llm(
                goal=new_goal,
                context=self.plan.context,
                max_tasks=10,
                llm_action=llm_action,
            )
            self.plan.add_tasks(tasks)

        logger.info(f"Updated plan, now has {len(self.plan.tasks)} tasks")

    def get_next_task(self) -> Optional[Task]:
        """Get the next task to execute.

        Returns:
            Next Task or None if plan is complete
        """
        return self.plan.current_task

    def finish_task(
        self,
        task_id: str,
        success: bool = True,
        result: str = "",
        code: str = "",
    ):
        """Mark a task as finished.

        Args:
            task_id: Task ID
            success: Whether task succeeded
            result: Task result
            code: Generated code (if applicable)
        """
        task = self.plan.get_task_by_id(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found in plan")
            return

        task.is_finished = True
        task.is_success = success
        task.result = result
        task.code = code

        # Update current task
        self.plan._update_current_task()

        logger.info(
            f"Finished task {task_id}: success={success}, "
            f"remaining={len(self.plan.get_pending_tasks())}"
        )

    async def process_task_result(
        self,
        task_id: str,
        result: str,
        review_action: Optional[Action] = None,
    ) -> tuple[str, bool]:
        """Process task result and potentially review it.

        Args:
            task_id: Task ID
            result: Task result
            review_action: Optional action to review the result

        Returns:
            Tuple of (review_feedback, confirmed)
        """
        task = self.plan.get_task_by_id(task_id)
        if not task:
            return ("Task not found", False)

        # If review action provided, get review
        if review_action:
            review = await self._review_task_result(task, result, review_action)
            return review

        # Otherwise, auto-confirm
        return ("Auto-confirmed", True)

    async def _review_task_result(
        self,
        task: Task,
        result: str,
        review_action: Action,
    ) -> tuple[str, bool]:
        """Review task result using LLM.

        Args:
            task: Task being reviewed
            result: Task result
            review_action: Action to perform review

        Returns:
            Tuple of (review_feedback, approved)
        """
        review_prompt = f"""
Review the following task result:

Task: {task.instruction}
Result: {result}

Is this result satisfactory? Respond with:
- "APPROVED" if the result is good
- "REDO" if the task should be redone
- "REVISE: <feedback>" if the result needs revision

Your review:
"""

        try:
            review_result = await review_action.run(review_prompt)
            review_text = str(review_result)

            if "APPROVED" in review_text.upper():
                return (review_text, True)
            else:
                return (review_text, False)

        except Exception as e:
            logger.error(f"Failed to review task result: {e}")
            return ("Review failed, auto-approving", True)

    def get_useful_memories(self, n: int = 10) -> List[Message]:
        """Get useful memories for the current task.

        Args:
            n: Number of memories to retrieve

        Returns:
            List of relevant messages
        """
        if not self.plan.current_task:
            return []

        # Get recent memories from working memory
        return self.working_memory.get(k=n)

    def add_memory(self, message: Message):
        """Add a message to working memory.

        Args:
            message: Message to add
        """
        self.working_memory.add(message)

    def clear_working_memory(self):
        """Clear the working memory."""
        self.working_memory = Memory()

    def get_plan_summary(self) -> Dict[str, Any]:
        """Get a summary of the current plan.

        Returns:
            Dictionary with plan summary
        """
        return {
            "goal": self.plan.goal,
            "total_tasks": len(self.plan.tasks),
            "finished_tasks": len(self.plan.get_finished_tasks()),
            "pending_tasks": len(self.plan.get_pending_tasks()),
            "progress": self.plan.progress,
            "is_completed": self.plan.is_completed,
            "is_successful": self.plan.is_successful,
            "current_task": (
                self.plan.current_task.instruction
                if self.plan.current_task
                else None
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize planner to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "plan": self.plan.to_dict(),
            "auto_run": self.auto_run,
            "use_llm_for_planning": self.use_llm_for_planning,
            "working_memory_size": len(self.working_memory.storage),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Planner":
        """Deserialize planner from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Planner instance
        """
        planner = cls(
            goal=data.get("plan", {}).get("goal", ""),
            auto_run=data.get("auto_run", False),
            use_llm_for_planning=data.get("use_llm_for_planning", True),
        )

        if "plan" in data:
            planner.plan = Plan.from_dict(data["plan"])

        return planner
