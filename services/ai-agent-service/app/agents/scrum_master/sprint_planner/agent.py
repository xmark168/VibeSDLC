"""Sprint Planner Agent - LangGraph workflow for sprint planning.

This agent creates detailed sprint plans from sprint backlog items.
Workflow: initialize -> generate -> evaluate -> refine -> finalize -> preview
"""

import os
from typing import Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langfuse.langchain import CallbackHandler
import json

from .state import SprintPlannerState
from .prompts import (
    INITIALIZE_PROMPT,
    GENERATE_PROMPT,
    EVALUATE_PROMPT,
    REFINE_PROMPT,
    FINALIZE_PROMPT,
    ASSIGN_PROMPT
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

        # Initialize Langfuse callback handler
        try:
            self.langfuse_handler = CallbackHandler(
                flush_at=5,  # Flush every 5 events to avoid 413 errors
                flush_interval=1.0
            )
        except Exception:
            # Fallback for older versions without flush_at parameter
            self.langfuse_handler = CallbackHandler()

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
        workflow.add_node("assign", self.assign_node)
        workflow.add_node("evaluate", self.evaluate_node)
        workflow.add_node("refine", self.refine_node)
        workflow.add_node("finalize", self.finalize_node)
        workflow.add_node("preview", self.preview_node)

        # Add edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "generate")
        workflow.add_edge("generate", "assign")
        workflow.add_edge("assign", "evaluate")

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

            # Merge enriched items with original backlog items
            enriched_from_llm = result.get("enriched_items", result.get("enriched_tasks", []))
            state.enriched_items = self._merge_enriched_items(state.sprint_backlog_items, enriched_from_llm)

            print(f"[Generate] Generated {len(state.daily_breakdown)} days plan")
            print(f"[Generate] Enriched {len(state.enriched_items)} items with rank, story_point, estimate_value, task_type, acceptance_criteria, dependencies")
            state.status = "generated"

        except json.JSONDecodeError as e:
            print(f"[Generate] JSON parse error: {e}")
            state.status = "error"

        return state

    def _merge_enriched_items(self, backlog_items: list[dict], enriched_items: list[dict]) -> list[dict]:
        """Merge enriched items with original backlog items.

        Args:
            backlog_items: Original backlog items from backlog.json
            enriched_items: Enriched items from LLM

        Returns:
            Merged items with all information (no nulls)
        """
        # Create a map of enriched items by ID
        enriched_map = {item.get("id"): item for item in enriched_items}

        # Create a map of all items by ID for dependency resolution
        all_items_map = {item.get("id"): item for item in backlog_items}

        # Merge with backlog items
        merged = []
        for idx, backlog_item in enumerate(backlog_items, 1):
            item_id = backlog_item.get("id")
            enriched = enriched_map.get(item_id, {})
            parent_id = backlog_item.get("parent_id")

            # Get dependencies from LLM or create based on parent_id
            dependencies = enriched.get("dependencies") or backlog_item.get("dependencies") or []

            # If no dependencies but has parent_id, add parent as dependency
            if not dependencies and parent_id and parent_id in all_items_map:
                dependencies = [parent_id]

            # If still no dependencies, try to find related items
            if not dependencies:
                dependencies = self._find_related_dependencies(item_id, backlog_item, all_items_map)

            # Merge: enriched fields override backlog fields, with defaults for nulls
            merged_item = {
                # Original backlog fields
                "id": backlog_item.get("id"),
                "type": backlog_item.get("type"),
                "parent_id": backlog_item.get("parent_id"),
                "title": backlog_item.get("title"),
                "description": backlog_item.get("description"),
                "labels": backlog_item.get("labels", []),
                "business_value": backlog_item.get("business_value", ""),
                "status": backlog_item.get("status", "Backlog"),

                # Enriched fields (from LLM with fallback defaults)
                "rank": enriched.get("rank") or backlog_item.get("rank") or idx,
                "story_point": enriched.get("story_point") or backlog_item.get("story_point") or 5,
                "estimate_value": enriched.get("estimate_value") or backlog_item.get("estimate_value") or 10,
                "task_type": enriched.get("task_type") or backlog_item.get("task_type") or "Development",
                "acceptance_criteria": enriched.get("acceptance_criteria") or backlog_item.get("acceptance_criteria") or ["Acceptance criteria to be defined"],
                "dependencies": dependencies,
                "deadline": enriched.get("deadline") or "2025-10-29",
                "plan_status": enriched.get("status") or "planned"
            }

            merged.append(merged_item)

        return merged

    def _find_related_dependencies(self, item_id: str, item: dict, all_items_map: dict) -> list[str]:
        """Find related dependencies for an item.

        Args:
            item_id: Current item ID
            item: Current item dict
            all_items_map: Map of all items by ID

        Returns:
            List of dependency IDs
        """
        dependencies = []
        item_type = item.get("type", "")
        item_title = item.get("title", "").lower()

        # For Testing tasks, find related Development tasks
        if "test" in item_type.lower() or "test" in item_title:
            for other_id, other_item in all_items_map.items():
                if other_id != item_id:
                    other_type = other_item.get("type", "").lower()
                    if "user story" in other_type or "task" in other_type:
                        # Testing depends on Development
                        dependencies.append(other_id)
                        if len(dependencies) >= 2:
                            break

        # For User Stories, find related Epics
        elif "user story" in item_type.lower():
            parent_id = item.get("parent_id")
            if parent_id and parent_id in all_items_map:
                dependencies.append(parent_id)

        # For Tasks, find related User Stories
        elif "task" in item_type.lower():
            parent_id = item.get("parent_id")
            if parent_id and parent_id in all_items_map:
                dependencies.append(parent_id)

        return dependencies

    def assign_node(self, state: SprintPlannerState) -> SprintPlannerState:
        """Assign tasks to team members.

        Args:
            state: Current state

        Returns:
            Updated state with task assignments
        """
        print(f"[Assign] Assigning {len(state.enriched_items)} items to team members...")

        if not state.enriched_items or not state.team_members:
            print(f"[Assign] No items or team members to assign")
            return state

        # Prepare prompt
        prompt = ASSIGN_PROMPT.format(
            enriched_items=json.dumps(state.enriched_items, indent=2),
            team_members=json.dumps(state.team_members, indent=2)
        )

        # Invoke LLM
        messages = [
            SystemMessage(content="You are a task assignment expert. Assign tasks to team members based on their roles and capacity."),
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
            state.task_assignments = result.get("task_assignments", [])

            print(f"[Assign] Assigned {len(state.task_assignments)} tasks")
            state.status = "assigned"

        except json.JSONDecodeError as e:
            print(f"[Assign] JSON parse error: {e}")
            # Fallback: create simple assignments
            state.task_assignments = self._create_default_assignments(state)
            print(f"[Assign] Created {len(state.task_assignments)} default assignments")

        return state

    def _create_default_assignments(self, state: SprintPlannerState) -> list[dict]:
        """Create default task assignments when LLM fails.

        Args:
            state: Current state

        Returns:
            List of task assignments
        """
        assignments = []
        team_members = state.team_members or []

        if not team_members:
            return assignments

        # Group team members by role
        developers = [m for m in team_members if m.get("role") == "Developer"]
        testers = [m for m in team_members if m.get("role") == "Tester"]
        designers = [m for m in team_members if m.get("role") == "Designer"]

        dev_idx = 0
        tester_idx = 0
        designer_idx = 0

        for item in state.enriched_items:
            item_id = item.get("id", "")
            task_type = item.get("task_type", "Development")
            story_point = item.get("story_point", 5)

            # Estimate hours based on story points (1 point = 2 hours)
            estimated_hours = (story_point or 5) * 2

            if task_type == "Testing" and testers:
                assignee = testers[tester_idx % len(testers)]
                tester_idx += 1
            elif task_type == "Design" and designers:
                assignee = designers[designer_idx % len(designers)]
                designer_idx += 1
            elif developers:
                assignee = developers[dev_idx % len(developers)]
                dev_idx += 1
            else:
                continue

            assignments.append({
                "item_id": item_id,
                "assignee": assignee.get("name", "Unknown"),
                "role": assignee.get("role", "Developer"),
                "estimated_hours": estimated_hours
            })

        return assignments

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
            # Threshold reduced from 0.8 to 0.7 for consistency with evaluate_branch
            if state.plan_score >= 0.7:
                state.user_approval = "approve"
                print("[Preview] Auto-approved (score >= 0.7)")
            elif state.current_loop >= state.max_loops:
                # Force approve if we've reached max loops
                state.user_approval = "approve"
                print(f"[Preview] Auto-approved (max loops {state.max_loops} reached, score: {state.plan_score})")
            else:
                state.user_approval = "edit"
                state.user_feedback = "Plan score too low, please refine"
                print(f"[Preview] Auto-edit (score {state.plan_score} < 0.7, loop {state.current_loop}/{state.max_loops})")

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
        # Threshold reduced from 0.8 to 0.7 for better performance
        if state.plan_score < 0.7 and state.current_loop < state.max_loops:
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
        sprint_number: int = 1,
        sprint_goal: str = "",
        start_date: str = "",
        end_date: str = "",
        sprint_duration_days: int = 14,
        velocity_plan: int = 0,
        sprint_backlog_items: list[dict] = None,
        team_capacity: dict = None,
        team_members: list[dict] = None,
        thread_id: str = None
    ) -> dict:
        """Run sprint planning workflow.

        Args:
            sprint_id: Sprint ID
            sprint_number: Sprint number
            sprint_goal: Sprint goal
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            sprint_duration_days: Sprint duration in days
            velocity_plan: Velocity plan from PO
            sprint_backlog_items: List of backlog items (raw from backlog.json)
            team_capacity: Team capacity dict
            team_members: List of team members
            thread_id: Thread ID for conversation

        Returns:
            Final sprint plan dict with enriched items, assignments, daily breakdown
        """
        # Initialize state
        initial_state = SprintPlannerState(
            sprint_id=sprint_id,
            sprint_number=sprint_number,
            sprint_goal=sprint_goal,
            start_date=start_date,
            end_date=end_date,
            sprint_duration_days=sprint_duration_days,
            velocity_plan=velocity_plan,
            sprint_backlog_items=sprint_backlog_items or [],
            team_capacity=team_capacity or {"dev_hours": 80, "qa_hours": 40},
            team_members=team_members or [],
            max_loops=1,
            current_loop=0,
            status="initial"
        )

        # Run graph
        print(f"\n{'='*60}")
        print(f"Starting Sprint Planner: {sprint_id}")
        print(f"{'='*60}\n")

        # Configure recursion limit and Langfuse tracing
        config = {
            "recursion_limit": 50,
            "callbacks": [self.langfuse_handler],
            "metadata": {
                "langfuse_session_id": self.session_id,
                "langfuse_user_id": self.user_id,
                "langfuse_tags": ["sprint_planner_agent", f"sprint_{sprint_id}"]
            }
        }

        try:
            final_state = self.graph.invoke(initial_state, config=config)
        finally:
            # Flush Langfuse to ensure all traces are sent
            try:
                self.langfuse_handler.langfuse.flush()
            except Exception:
                pass  # Ignore flush errors

        # LangGraph returns dict, not SprintPlannerState object
        if isinstance(final_state, dict):
            status = final_state.get("status", "unknown")
            sprint_plan = final_state.get("sprint_plan", {})
            plan_score = final_state.get("plan_score", 0.0)
            daily_breakdown = final_state.get("daily_breakdown", [])
            resource_allocation = final_state.get("resource_allocation", {})
            enriched_items = final_state.get("enriched_items", [])
            task_assignments = final_state.get("task_assignments", [])
        else:
            status = final_state.status
            sprint_plan = final_state.sprint_plan
            plan_score = final_state.plan_score
            daily_breakdown = final_state.daily_breakdown
            resource_allocation = final_state.resource_allocation
            enriched_items = final_state.enriched_items
            task_assignments = final_state.task_assignments

        print(f"\n{'='*60}")
        print(f"Sprint Planning Complete: {status}")
        print(f"{'='*60}\n")

        return {
            "sprint_plan": sprint_plan,
            "status": status,
            "plan_score": plan_score,
            "daily_breakdown": daily_breakdown,
            "resource_allocation": resource_allocation,
            "enriched_items": enriched_items,
            "task_assignments": task_assignments
        }

    # ==================== PROCESS PO OUTPUT METHOD ====================

    def process_po_output(self, po_output: dict, team: dict = None) -> dict:
        """Process Product Owner output end-to-end.

        This method owns the complete planning workflow:
        1. Receive and transform PO output
        2. Calculate acceptance criteria and estimates
        3. Check Definition of Ready
        4. Run sprint planning for each sprint
        5. Assign tasks to team

        Args:
            po_output: PO output with metadata, prioritized_backlog, sprints
            team: Team members dict (optional)

        Returns:
            dict: Complete processed output with sprints, items, assignments
        """
        from .tools import (
            receive_po_output,
            calculate_acceptance_criteria_and_estimates,
            check_definition_of_ready,
            assign_tasks_to_team
        )
        from ..models import ScrumMasterOutput
        from datetime import datetime
        import json

        print("\n" + "="*80)
        print("🎯 SPRINT PLANNER: Process PO Output (End-to-End)")
        print("="*80)

        try:
            # Step 1: Receive and transform
            print("\n📥 Step 1: Transform PO Output...")
            transform_result = receive_po_output.invoke({"sprint_plan": po_output})

            if not transform_result["success"]:
                return {
                    "success": False,
                    "error": transform_result.get("error"),
                    "step": "transform"
                }

            backlog_items = transform_result["backlog_items"]
            sprints = transform_result["sprints"]

            # Step 2: Calculate AC & Estimates
            print("\n🧮 Step 2: Calculate Acceptance Criteria & Estimates...")
            calc_result = calculate_acceptance_criteria_and_estimates.invoke({"backlog_items": backlog_items})
            backlog_items = calc_result["updated_items"]

            # Step 3: Run sprint planning for each sprint (enrich with rank, SP, deadline)
            print("\n📅 Step 3: Run Sprint Planning Workflow...")
            enriched_items = []

            for sprint in sprints:
                sprint_id = sprint.get("id")
                sprint_goal = sprint.get("goal", "")
                sprint_duration = sprint.get("duration_days", 14)

                sprint_backlog = [
                    item for item in backlog_items
                    if item.get("sprint_id") == sprint_id
                ]

                if sprint_backlog:
                    print(f"\n   📋 Planning {sprint_id}: {len(sprint_backlog)} tasks")

                    # Convert datetime to string
                    sprint_backlog_serializable = []
                    for item in sprint_backlog:
                        item_copy = item.copy()
                        for key, value in item_copy.items():
                            if isinstance(value, datetime):
                                item_copy[key] = value.isoformat()
                        sprint_backlog_serializable.append(item_copy)

                    # Run planning workflow
                    planner_result = self.run(
                        sprint_id=sprint_id,
                        sprint_goal=sprint_goal,
                        sprint_backlog_items=sprint_backlog_serializable,
                        sprint_duration_days=sprint_duration,
                        team_capacity={"dev_hours": 80, "qa_hours": 40}
                    )

                    # Merge enriched data
                    enriched_tasks = planner_result.get("enriched_tasks", [])

                    for item in sprint_backlog:
                        enriched = next(
                            (t for t in enriched_tasks if t.get("task_id") == item.get("id")),
                            None
                        )

                        if enriched:
                            item["rank"] = enriched.get("rank")
                            item["story_point"] = enriched.get("story_point")
                            item["deadline"] = enriched.get("deadline")
                            item["status"] = enriched.get("status", "TODO")
                            print(f"      ✅ {item['id']}: rank={item['rank']}, sp={item['story_point']}")

                        enriched_items.append(item)

            if enriched_items:
                backlog_items = enriched_items

            # Step 4: Check DoR
            print("\n✅ Step 4: Check Definition of Ready...")
            dor_result = check_definition_of_ready.invoke({"backlog_items": backlog_items})

            # Step 5: Assign tasks
            print("\n👥 Step 5: Assign Tasks to Team...")
            assignment_result = assign_tasks_to_team.invoke({
                "backlog_items": backlog_items,
                "team": team
            })

            updated_items = assignment_result["updated_items"]

            # Create output
            output = ScrumMasterOutput(
                sprints=sprints,
                backlog_items=updated_items,
                assignments=assignment_result["assignments"],
                dor_results=dor_result["results"],
                summary={
                    **transform_result["summary"],
                    "dor_pass_rate": dor_result["pass_rate"],
                    "total_assigned": assignment_result["total_assigned"],
                    "processed_at": datetime.now().isoformat()
                }
            )

            # Save to file
            output_file = f"sprint_planner_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output.model_dump(), f, indent=2, ensure_ascii=False, default=str)

            print("\n" + "="*80)
            print("✅ SPRINT PLANNER: Processing Complete")
            print("="*80)
            print(f"\n📊 Summary:")
            print(f"  - Sprints: {len(sprints)}")
            print(f"  - Items: {len(updated_items)}")
            print(f"  - Assigned: {assignment_result['total_assigned']}")
            print(f"  - DoR Pass: {dor_result['pass_rate']:.1%}")
            print(f"\n💾 Output: {output_file}")

            return {
                "success": True,
                "output": output.model_dump(),
                "output_file": output_file,
                "summary": output.summary
            }

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "step": "unknown"
            }
