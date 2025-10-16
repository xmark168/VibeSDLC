"""Sprint Planner Agent - LangGraph workflow for sprint planning.

This agent creates detailed sprint plans from sprint backlog items.
Workflow: initialize -> generate -> evaluate -> refine -> finalize -> preview
"""

import os
from typing import Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

from .state import SprintPlannerState
from .prompts import (
    INITIALIZE_PROMPT,
    GENERATE_PROMPT,
    EVALUATE_PROMPT,
    REFINE_PROMPT,
    FINALIZE_PROMPT
)
from .tools import (
    validate_sprint_capacity,
    check_task_dependencies,
    calculate_resource_balance,
    export_to_kanban
)


class SprintPlannerAgent:
    """Sprint Planner Agent using LangGraph workflow."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.2
    ):
        """Initialize Sprint Planner Agent.

        Args:
            session_id: Session ID for Langfuse tracing
            user_id: User ID for tracking
            model_name: OpenAI model name (default: gpt-4o-mini)
            temperature: LLM temperature (default: 0.2 for balanced reasoning)
        """
        self.session_id = session_id
        self.user_id = user_id

        # Initialize LLM with OpenAI
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow with nodes and edges.

        Returns:
            Compiled StateGraph
        """
        # Create graph
        workflow = StateGraph(SprintPlannerState)

        # Add nodes
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("generate", self.generate_node)
        workflow.add_node("evaluate", self.evaluate_node)
        workflow.add_node("refine", self.refine_node)
        workflow.add_node("finalize", self.finalize_node)
        workflow.add_node("preview", self.preview_node)

        # Add edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "generate")
        workflow.add_edge("generate", "evaluate")

        # Conditional edge: evaluate -> refine or finalize
        workflow.add_conditional_edges(
            "evaluate",
            self.evaluate_branch,
            {
                "refine": "refine",
                "finalize": "finalize"
            }
        )

        workflow.add_edge("refine", "evaluate")
        workflow.add_edge("finalize", "preview")

        # Conditional edge: preview -> approve or edit
        workflow.add_conditional_edges(
            "preview",
            self.preview_branch,
            {
                "approve": END,
                "edit": "refine"
            }
        )

        return workflow.compile()

    # ==================== NODES ====================

    def initialize_node(self, state: SprintPlannerState) -> SprintPlannerState:
        """Initialize sprint planning - validate inputs.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        print(f"[Initialize] Sprint: {state.sprint_id}, Goal: {state.sprint_goal}")

        # Validate inputs
        if not state.sprint_backlog_items:
            state.status = "error"
            return state

        # Calculate total effort
        total_effort = sum(
            item.get("effort", 0)
            for item in state.sprint_backlog_items
        )

        print(f"[Initialize] Total tasks: {len(state.sprint_backlog_items)}, Effort: {total_effort}")

        # Validate capacity
        capacity_result = validate_sprint_capacity.invoke({
            "team_capacity": state.team_capacity,
            "required_effort": total_effort
        })

        if not capacity_result.get("valid"):
            print(f"[Initialize] Capacity warning: {capacity_result.get('recommendation')}")

        state.status = "initialized"
        return state

    def generate_node(self, state: SprintPlannerState) -> SprintPlannerState:
        """Generate sprint plan with daily breakdown and resource allocation.

        Args:
            state: Current state

        Returns:
            Updated state with generated plan
        """
        print(f"[Generate] Creating sprint plan...")

        # Calculate sprint start date (today or specified)
        from datetime import datetime, timedelta
        sprint_start_date = datetime.now().strftime("%Y-%m-%d")

        # Prepare prompt
        prompt = GENERATE_PROMPT.format(
            sprint_id=state.sprint_id,
            sprint_goal=state.sprint_goal,
            sprint_duration_days=state.sprint_duration_days,
            sprint_start_date=sprint_start_date,
            team_capacity=json.dumps(state.team_capacity, indent=2),
            sprint_backlog_items=json.dumps(state.sprint_backlog_items, indent=2)
        )

        # Invoke LLM
        messages = [
            SystemMessage(content="You are a sprint planning expert."),
            HumanMessage(content=prompt)
        ]

        response = self.llm.invoke(messages)

        # Parse JSON response
        try:
            content = response.content
            # Extract JSON from markdown code block if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # Update state
            state.daily_breakdown = result.get("daily_breakdown", [])
            state.resource_allocation = result.get("resource_allocation", {})
            state.enriched_tasks = result.get("enriched_tasks", [])

            print(f"[Generate] Generated {len(state.daily_breakdown)} days plan")
            print(f"[Generate] Enriched {len(state.enriched_tasks)} tasks with rank, story_point, deadline, status")
            state.status = "generated"

        except json.JSONDecodeError as e:
            print(f"[Generate] JSON parse error: {e}")
            state.status = "error"

        return state

    def evaluate_node(self, state: SprintPlannerState) -> SprintPlannerState:
        """Evaluate sprint plan quality.

        Args:
            state: Current state

        Returns:
            Updated state with evaluation results
        """
        # Increment loop counter FIRST
        state.current_loop += 1
        print(f"[Evaluate] Evaluating plan (loop {state.current_loop}/{state.max_loops})...")

        # Prepare sprint plan for evaluation
        sprint_plan = {
            "sprint_id": state.sprint_id,
            "sprint_goal": state.sprint_goal,
            "daily_breakdown": state.daily_breakdown,
            "resource_allocation": state.resource_allocation
        }

        # Prepare prompt
        prompt = EVALUATE_PROMPT.format(
            sprint_plan=json.dumps(sprint_plan, indent=2)
        )

        # Invoke LLM
        messages = [
            SystemMessage(content="You are a sprint planning evaluator."),
            HumanMessage(content=prompt)
        ]

        response = self.llm.invoke(messages)

        # Parse JSON response
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # Update state
            state.plan_score = result.get("plan_score", 0.0)
            state.can_proceed = result.get("can_proceed", False)
            state.capacity_issues = result.get("capacity_issues", [])
            state.dependency_conflicts = result.get("dependency_conflicts", [])
            state.recommendations = result.get("recommendations", [])

            print(f"[Evaluate] Score: {state.plan_score}, Can proceed: {state.can_proceed}")

            # Use tools to validate
            self._validate_with_tools(state)

            state.status = "evaluated"

        except json.JSONDecodeError as e:
            print(f"[Evaluate] JSON parse error: {e}")
            state.plan_score = 0.0
            state.can_proceed = False

        return state

    def _validate_with_tools(self, state: SprintPlannerState):
        """Validate plan using tools.

        Args:
            state: Current state (modified in place)
        """
        # Check dependencies
        dependency_result = check_task_dependencies.invoke({
            "tasks": state.sprint_backlog_items,
            "daily_breakdown": state.daily_breakdown
        })

        if not dependency_result.get("valid"):
            print(f"[Validate] Dependency conflicts: {dependency_result.get('total_conflicts')}")
            state.dependency_conflicts.extend(dependency_result.get("conflicts", []))

        # Check resource balance
        balance_result = calculate_resource_balance.invoke({
            "resource_allocation": state.resource_allocation
        })

        print(f"[Validate] Balance score: {balance_result.get('balance_score')}")
        if balance_result.get("overloaded_resources"):
            print(f"[Validate] Overloaded: {balance_result.get('overloaded_resources')}")

    def refine_node(self, state: SprintPlannerState) -> SprintPlannerState:
        """Refine sprint plan based on evaluation feedback.

        Args:
            state: Current state

        Returns:
            Updated state with refined plan
        """
        print(f"[Refine] Refining plan based on feedback...")

        # Prepare current plan
        sprint_plan = {
            "daily_breakdown": state.daily_breakdown,
            "resource_allocation": state.resource_allocation
        }

        # Prepare issues and recommendations
        issues = {
            "capacity_issues": state.capacity_issues,
            "dependency_conflicts": state.dependency_conflicts
        }

        # Prepare prompt
        prompt = REFINE_PROMPT.format(
            sprint_plan=json.dumps(sprint_plan, indent=2),
            issues=json.dumps(issues, indent=2),
            recommendations=json.dumps(state.recommendations, indent=2)
        )

        # Add user feedback if provided
        if state.user_feedback:
            prompt += f"\n\nUser Feedback:\n{state.user_feedback}"

        # Invoke LLM
        messages = [
            SystemMessage(content="You are a sprint planning refiner."),
            HumanMessage(content=prompt)
        ]

        response = self.llm.invoke(messages)

        # Parse JSON response
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # Update state with refined plan
            state.daily_breakdown = result.get("daily_breakdown", state.daily_breakdown)
            state.resource_allocation = result.get("resource_allocation", state.resource_allocation)

            changes = result.get("changes_made", [])
            print(f"[Refine] Made {len(changes)} changes")

            state.status = "refined"
            state.user_feedback = None  # Clear feedback after processing

        except json.JSONDecodeError as e:
            print(f"[Refine] JSON parse error: {e}")
            state.status = "error"

        return state

    def finalize_node(self, state: SprintPlannerState) -> SprintPlannerState:
        """Finalize sprint plan - create summary and export.

        Args:
            state: Current state

        Returns:
            Updated state with finalized plan
        """
        print(f"[Finalize] Finalizing sprint plan...")

        # Prepare current plan
        sprint_plan = {
            "sprint_id": state.sprint_id,
            "sprint_goal": state.sprint_goal,
            "duration_days": state.sprint_duration_days,
            "daily_breakdown": state.daily_breakdown,
            "resource_allocation": state.resource_allocation
        }

        # Prepare prompt
        prompt = FINALIZE_PROMPT.format(
            sprint_plan=json.dumps(sprint_plan, indent=2),
            sprint_id=state.sprint_id
        )

        # Invoke LLM
        messages = [
            SystemMessage(content="You are a sprint planning finalizer."),
            HumanMessage(content=prompt)
        ]

        response = self.llm.invoke(messages)

        # Parse JSON response
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # Update state with finalized plan
            state.sprint_plan = result.get("sprint_plan", sprint_plan)

            # Export to Kanban
            kanban_result = export_to_kanban.invoke({
                "sprint_plan": state.sprint_plan
            })

            if kanban_result.get("success"):
                print(f"[Finalize] Exported {kanban_result.get('total_cards')} cards to Kanban")

            state.status = "finalized"

        except json.JSONDecodeError as e:
            print(f"[Finalize] JSON parse error: {e}")
            state.sprint_plan = sprint_plan
            state.status = "error"

        return state

    def preview_node(self, state: SprintPlannerState) -> SprintPlannerState:
        """Preview sprint plan for user approval.

        Args:
            state: Current state

        Returns:
            Updated state (waiting for user input)
        """
        print(f"[Preview] Sprint plan ready for review")
        print("=" * 60)
        print(f"Sprint: {state.sprint_id}")
        print(f"Goal: {state.sprint_goal}")
        print(f"Days: {len(state.daily_breakdown)}")
        print(f"Plan Score: {state.plan_score}")
        print("=" * 60)

        # In production, this would trigger a human-in-the-loop checkpoint
        # For now, we auto-approve if score is good OR we've exhausted loops
        if state.user_approval is None:
            if state.plan_score >= 0.8:
                state.user_approval = "approve"
                print("[Preview] Auto-approved (score >= 0.8)")
            elif state.current_loop >= state.max_loops:
                # Force approve if we've reached max loops
                state.user_approval = "approve"
                print(f"[Preview] Auto-approved (max loops {state.max_loops} reached, score: {state.plan_score})")
            else:
                state.user_approval = "edit"
                state.user_feedback = "Plan score too low, please refine"
                print(f"[Preview] Auto-edit (score {state.plan_score} < 0.8, loop {state.current_loop}/{state.max_loops})")

        state.status = "preview"
        return state

    # ==================== CONDITIONAL BRANCHES ====================

    def evaluate_branch(self, state: SprintPlannerState) -> Literal["refine", "finalize"]:
        """Decide whether to refine or finalize based on evaluation.

        Args:
            state: Current state

        Returns:
            "refine" or "finalize"
        """
        # Refine if score is low and we have loops left
        # Note: current_loop is already incremented in evaluate_node
        if state.plan_score < 0.8 and state.current_loop < state.max_loops:
            print(f"[Branch] -> refine (score: {state.plan_score}, loop: {state.current_loop}/{state.max_loops})")
            return "refine"

        # Otherwise finalize
        print(f"[Branch] -> finalize (score: {state.plan_score}, loop: {state.current_loop}/{state.max_loops})")
        return "finalize"

    def preview_branch(self, state: SprintPlannerState) -> Literal["approve", "edit"]:
        """Decide whether to approve or edit based on user input.

        Args:
            state: Current state

        Returns:
            "approve" or "edit"
        """
        if state.user_approval == "approve":
            print("[Branch] -> approve")
            state.status = "completed"
            return "approve"
        else:
            print("[Branch] -> edit")
            return "edit"

    # ==================== RUN METHOD ====================

    def run(
        self,
        sprint_id: str,
        sprint_goal: str,
        sprint_backlog_items: list[dict],
        sprint_duration_days: int = 14,
        team_capacity: dict = None,
        thread_id: str = None
    ) -> dict:
        """Run sprint planning workflow.

        Args:
            sprint_id: Sprint ID
            sprint_goal: Sprint goal
            sprint_backlog_items: List of backlog items
            sprint_duration_days: Sprint duration in days
            team_capacity: Team capacity dict
            thread_id: Thread ID for conversation

        Returns:
            Final sprint plan dict
        """
        # Initialize state
        initial_state = SprintPlannerState(
            sprint_id=sprint_id,
            sprint_goal=sprint_goal,
            sprint_backlog_items=sprint_backlog_items,
            sprint_duration_days=sprint_duration_days,
            team_capacity=team_capacity or {"dev_hours": 80, "qa_hours": 40},
            max_loops=2,
            current_loop=0,
            status="initial"
        )

        # Run graph
        print(f"\n{'='*60}")
        print(f"Starting Sprint Planner: {sprint_id}")
        print(f"{'='*60}\n")

        # Configure recursion limit (default 25, we set to 50 for safety)
        config = {
            "recursion_limit": 50
        }

        final_state = self.graph.invoke(initial_state, config=config)

        # LangGraph returns dict, not SprintPlannerState object
        if isinstance(final_state, dict):
            status = final_state.get("status", "unknown")
            sprint_plan = final_state.get("sprint_plan", {})
            plan_score = final_state.get("plan_score", 0.0)
            daily_breakdown = final_state.get("daily_breakdown", [])
            resource_allocation = final_state.get("resource_allocation", {})
            enriched_tasks = final_state.get("enriched_tasks", [])
        else:
            status = final_state.status
            sprint_plan = final_state.sprint_plan
            plan_score = final_state.plan_score
            daily_breakdown = final_state.daily_breakdown
            resource_allocation = final_state.resource_allocation
            enriched_tasks = final_state.enriched_tasks

        print(f"\n{'='*60}")
        print(f"Sprint Planning Complete: {status}")
        print(f"{'='*60}\n")

        return {
            "sprint_plan": sprint_plan,
            "status": status,
            "plan_score": plan_score,
            "daily_breakdown": daily_breakdown,
            "resource_allocation": resource_allocation,
            "enriched_tasks": enriched_tasks
        }
