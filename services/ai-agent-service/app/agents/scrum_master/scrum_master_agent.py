"""Scrum Master Agent - Deep Agent orchestrator.

This is the main Scrum Master agent that wraps sprint_planner as a subagent tool.
Architecture: Deep Agent with sprint_planner subagent for sprint planning workflow.

DRAFT VERSION - No database connection, uses hardcoded test data.
Output format matches database schema for future integration.
"""

import os
import json
from typing import Annotated
from datetime import datetime
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from .sprint_planner.agent import SprintPlannerAgent
from .tools import (
    receive_po_output,
    check_definition_of_ready,
    calculate_acceptance_criteria_and_estimates,
    assign_tasks_to_team
)
from .models import ScrumMasterOutput
from .test_data import MOCK_TEAM
from app.templates.prompts.scrum_master.sm_agent import SYSTEM_PROMPT


class ScrumMasterAgent:
    """Scrum Master Agent - Deep Agent with sprint planning capabilities."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.2
    ):
        """Initialize Scrum Master Agent.

        Args:
            session_id: Session ID for Langfuse tracing
            user_id: User ID for tracking
            model_name: OpenAI model name (default: gpt-4o-mini)
            temperature: LLM temperature (default: 0.2 for balanced reasoning)
        """
        self.session_id = session_id
        self.user_id = user_id
        self.model_name = model_name
        self.temperature = temperature

        # Initialize LLM with OpenAI
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        # Create tools with self reference
        self.tools = self._create_tools()

        # Create deep agent
        self.agent = self._create_agent()

    def _analyze_and_assign_tasks_with_llm(self, backlog_items: list, team: dict) -> list:
        """Analyze team skills and assign tasks using LLM for intelligent matching.

        Args:
            backlog_items: List of backlog items to assign
            team: Team members dict with skills

        Returns:
            list: LLM-based assignment suggestions or None if failed
        """
        from langchain_core.messages import HumanMessage
        import re

        # Prepare team info for LLM
        team_info = "## Team Members:\n"
        for role, members in team.items():
            if isinstance(members, list):
                team_info += f"\n### {role.upper()}:\n"
                for member in members:
                    team_info += f"- {member['name']} ({member['id']}): {member['role']}\n"

        # Prepare backlog items for LLM
        items_info = "## Backlog Items to Assign:\n"
        for item in backlog_items:
            if item["type"] in ["Task", "Sub-task"]:
                items_info += f"- {item['id']}: {item['title']} (Type: {item.get('task_type', 'General')})\n"

        # Create prompt for LLM
        prompt = f"""Bạn là Scrum Master. Hãy giao việc cho team members dựa trên role của họ.

{team_info}

{items_info}

Quy tắc giao việc:
1. Development tasks → Developer agents (round-robin để cân bằng workload)
2. Testing tasks → Tester agents (round-robin để cân bằng workload)
3. Design tasks → Designer agents
4. General tasks → Developer agents (round-robin)

LƯU Ý: Không phân biệt Frontend/Backend developer, chỉ giao cho Developer agent.

Trả lời dưới dạng JSON:
{{
  "assignments": [
    {{"item_id": "...", "assignee_id": "...", "reason": "..."}},
    ...
  ]
}}"""

        try:
            # Call LLM
            response = self.llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                assignments_data = json.loads(json_match.group())
                return assignments_data.get("assignments", [])
        except Exception as e:
            print(f"⚠️  LLM-based assignment failed: {e}, falling back to round-robin")

        # Fallback to None if LLM fails
        return None

    def _create_tools(self) -> list:
        """Create tools for Scrum Master Agent.

        Returns:
            List of tool functions
        """
        # Closure to capture self reference
        scrum_master = self

        @tool
        def plan_sprint(
            sprint_id: str,
            sprint_goal: str,
            sprint_backlog_items: list[dict],
            sprint_duration_days: int = 14,
            team_capacity: dict = None
        ) -> Annotated[dict, "Sprint plan with daily breakdown and resource allocation"]:
            """Create a detailed sprint plan from backlog items.

            This tool orchestrates the entire sprint planning workflow:
            1. Initialize: Validate inputs and capacity
            2. Generate: Create daily breakdown and resource allocation
            3. Evaluate: Check plan quality, dependencies, and balance
            4. Refine: Improve plan based on evaluation (if needed)
            5. Finalize: Create summary and export to Kanban
            6. Preview: Show plan for approval

            Args:
                sprint_id: Unique sprint identifier (e.g., "sprint-1")
                sprint_goal: Sprint goal description
                sprint_backlog_items: List of backlog items to plan
                    Each item should have: id, title, description, type, effort, dependencies
                sprint_duration_days: Sprint duration in days (default: 14)
                team_capacity: Team capacity dict (e.g., {"dev_hours": 80, "qa_hours": 40})

            Returns:
                dict: Sprint plan with:
                    - sprint_plan: Full plan with daily breakdown
                    - status: Planning status (completed/error)
                    - plan_score: Quality score (0-1)
                    - daily_breakdown: Tasks by day
                    - resource_allocation: Resources by team member

            Example:
                >>> plan_sprint(
                ...     sprint_id="sprint-1",
                ...     sprint_goal="Implement authentication",
                ...     sprint_backlog_items=[
                ...         {"id": "TASK-1", "title": "Login API", "effort": 5, "type": "development"}
                ...     ],
                ...     team_capacity={"dev_hours": 80, "qa_hours": 40}
                ... )
            """
            try:
                # Create separate session_id for sprint planner
                tool_session_id = f"{scrum_master.session_id}_sprint_planner_tool"

                # Initialize Sprint Planner Agent
                sprint_planner = SprintPlannerAgent(
                    session_id=tool_session_id,
                    user_id=scrum_master.user_id,
                    model_name=scrum_master.model_name,
                    temperature=scrum_master.temperature
                )

                # Run sprint planning workflow
                result = sprint_planner.run(
                    sprint_id=sprint_id,
                    sprint_goal=sprint_goal,
                    sprint_backlog_items=sprint_backlog_items,
                    sprint_duration_days=sprint_duration_days,
                    team_capacity=team_capacity or {"dev_hours": 80, "qa_hours": 40},
                    thread_id=f"{tool_session_id}_thread"
                )

                return {
                    "success": True,
                    "sprint_id": sprint_id,
                    **result
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "sprint_id": sprint_id,
                    "status": "error"
                }

        @tool
        def get_sprint_status(sprint_id: str) -> Annotated[dict, "Current sprint status"]:
            """Get current status of a sprint.

            Args:
                sprint_id: Sprint ID to check

            Returns:
                dict: Sprint status information
            """
            # TODO: Implement sprint status tracking
            # This would query a database or state store
            return {
                "sprint_id": sprint_id,
                "status": "in_progress",
                "message": "Sprint status tracking not yet implemented"
            }

        @tool
        def update_sprint_task(
            sprint_id: str,
            task_id: str,
            status: str
        ) -> Annotated[dict, "Updated task status"]:
            """Update status of a sprint task.

            Args:
                sprint_id: Sprint ID
                task_id: Task ID to update
                status: New status (To Do, In Progress, Done)

            Returns:
                dict: Update result
            """
            # TODO: Implement task status updates
            # This would update Kanban board or database
            return {
                "success": True,
                "sprint_id": sprint_id,
                "task_id": task_id,
                "status": status,
                "message": f"Task {task_id} updated to {status}"
            }

        @tool
        def process_po_output(sprint_plan: dict) -> Annotated[dict, "Process Product Owner output and prepare for sprint"]:
            """Process Sprint Plan từ Product Owner và chuẩn bị cho sprint execution.

            Workflow:
            1. Receive và transform PO output to database format
            2. Calculate acceptance criteria và estimates (LLM-based)
            3. Check Definition of Ready (DoR) cho tất cả items
            4. Assign tasks to team members
            5. Export database-ready format

            Args:
                sprint_plan: Sprint Plan JSON từ Product Owner với:
                    - metadata: Product info
                    - prioritized_backlog: List of backlog items
                    - sprints: List of sprints with assigned items

            Returns:
                dict: Processed result với:
                    - sprints: Database-ready sprint records
                    - backlog_items: Database-ready backlog item records (with acceptance criteria & estimates)
                    - assignments: Task assignments
                    - dor_results: DoR check results
                    - summary: Statistics
            """
            try:
                print("\n" + "="*80)
                print("🎯 SCRUM MASTER: PROCESS PRODUCT OWNER OUTPUT")
                print("="*80)

                # Step 1: Receive and transform PO output
                print("\n📥 Step 1: Receive PO Output...")
                transform_result = receive_po_output.invoke({"sprint_plan": sprint_plan})

                if not transform_result["success"]:
                    return {
                        "success": False,
                        "error": transform_result.get("error"),
                        "step": "transform"
                    }

                backlog_items = transform_result["backlog_items"]
                sprints = transform_result["sprints"]

                # Step 2: Calculate Acceptance Criteria & Estimates (LLM-based)
                print("\n🧮 Step 2: Calculate Acceptance Criteria & Estimates...")
                calc_result = calculate_acceptance_criteria_and_estimates.invoke({"backlog_items": backlog_items})
                backlog_items = calc_result["updated_items"]

                # Step 2.5: Enrich tasks with Sprint Planner (rank, story_point, deadline, status)
                print("\n✨ Step 2.5: Enrich Tasks with Sprint Planner...")
                enriched_items = []

                for sprint in sprints:
                    sprint_id = sprint.get("id")
                    sprint_goal = sprint.get("goal", "")
                    sprint_duration = sprint.get("duration_days", 14)

                    # Get backlog items for this sprint
                    sprint_backlog = [
                        item for item in backlog_items
                        if item.get("sprint_id") == sprint_id
                    ]

                    if sprint_backlog:
                        print(f"   📋 Sprint {sprint_id}: {len(sprint_backlog)} tasks")

                        # Run Sprint Planner to enrich tasks
                        try:
                            from app.agents.scrum_master.sprint_planner.agent import SprintPlannerAgent
                            from datetime import datetime

                            # Convert datetime objects to strings for JSON serialization
                            sprint_backlog_serializable = []
                            for item in sprint_backlog:
                                item_copy = item.copy()
                                for key, value in item_copy.items():
                                    if isinstance(value, datetime):
                                        item_copy[key] = value.isoformat()
                                sprint_backlog_serializable.append(item_copy)

                            planner = SprintPlannerAgent(
                                session_id=scrum_master.session_id,
                                user_id=scrum_master.user_id,
                                model_name=scrum_master.model_name,
                                temperature=scrum_master.temperature
                            )

                            planner_result = planner.run(
                                sprint_id=sprint_id,
                                sprint_goal=sprint_goal,
                                sprint_backlog_items=sprint_backlog_serializable,
                                sprint_duration_days=sprint_duration,
                                team_capacity={"dev_hours": 80, "qa_hours": 40}
                            )

                            # Merge enriched data back to backlog items
                            enriched_tasks = planner_result.get("enriched_tasks", [])

                            for item in sprint_backlog:
                                # Find matching enriched task
                                enriched = next(
                                    (t for t in enriched_tasks if t.get("task_id") == item.get("id")),
                                    None
                                )

                                if enriched:
                                    item["rank"] = enriched.get("rank")
                                    item["story_point"] = enriched.get("story_point")
                                    item["deadline"] = enriched.get("deadline")
                                    item["status"] = enriched.get("status", "TODO")
                                    print(f"      ✅ {item['id']}: rank={item['rank']}, sp={item['story_point']}, deadline={item['deadline']}")

                                enriched_items.append(item)

                        except Exception as e:
                            print(f"      ⚠️  Sprint Planner error: {e}")
                            # Fall back to original items without enrichment
                            enriched_items.extend(sprint_backlog)
                    else:
                        print(f"   ℹ️  Sprint {sprint_id}: No tasks")

                # Update backlog_items with enriched data
                if enriched_items:
                    backlog_items = enriched_items
                    print(f"   ✅ Enriched {len(enriched_items)} tasks total")

                # Step 3: Check Definition of Ready
                print("\n✅ Step 3: Check Definition of Ready...")
                dor_result = check_definition_of_ready.invoke({"backlog_items": backlog_items})

                # Step 4: Assign tasks to team (with LLM-based skill matching)
                print("\n👥 Step 4: Assign Tasks to Team (LLM-based skill matching)...")

                # Try LLM-based assignment first
                llm_assignments = scrum_master._analyze_and_assign_tasks_with_llm(backlog_items, MOCK_TEAM)

                if llm_assignments:
                    print("✅ Using LLM-based intelligent assignment")
                    # TODO: Implement LLM assignment result processing
                    # For now, fall back to standard assignment
                    assignment_result = assign_tasks_to_team.invoke({
                        "backlog_items": backlog_items,
                        "team": MOCK_TEAM
                    })
                else:
                    print("ℹ️  Using standard round-robin assignment")
                    assignment_result = assign_tasks_to_team.invoke({
                        "backlog_items": backlog_items,
                        "team": MOCK_TEAM
                    })

                # Update backlog items with assignments
                updated_items = assignment_result["updated_items"]

                # Create final output
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

                # Save to file (instead of database)
                output_file = f"scrum_master_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output.model_dump(), f, indent=2, ensure_ascii=False, default=str)

                print("\n" + "="*80)
                print("✅ PROCESSING COMPLETE")
                print("="*80)
                print(f"\n📊 Summary:")
                print(f"  - Sprints: {len(sprints)}")
                print(f"  - Backlog Items: {len(updated_items)}")
                print(f"  - Tasks Assigned: {assignment_result['total_assigned']}")
                print(f"  - DoR Pass Rate: {dor_result['pass_rate']:.1%}")
                print(f"\n💾 Output saved to: {output_file}")

                return {
                    "success": True,
                    "output": output.model_dump(),
                    "output_file": output_file,
                    "summary": output.summary
                }

            except Exception as e:
                print(f"\n❌ Error processing PO output: {str(e)}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "error": str(e),
                    "step": "unknown"
                }

        return [plan_sprint, get_sprint_status, update_sprint_task, process_po_output]

    def _create_agent(self):
        """Create Deep Agent with tools and instructions.

        Returns:
            Compiled deep agent
        """
        instructions = self._get_instructions()

        agent = create_deep_agent(
            tools=self.tools,
            instructions=instructions,
            model=self.llm
        )

        return agent

    def _get_instructions(self) -> str:
        """Get system instructions for Scrum Master Agent.

        Returns:
            System prompt string from templates
        """
        return SYSTEM_PROMPT

    def run(self, user_message: str, thread_id: str = None) -> dict:
        """Run Scrum Master Agent with user message.

        Args:
            user_message: User input message
            thread_id: Thread ID for conversation

        Returns:
            Agent response dict
        """
        result = self.agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        })

        return result

    def chat(self, message: str) -> str:
        """Simple chat interface.

        Args:
            message: User message

        Returns:
            Agent response text
        """
        result = self.run(message)
        final_message = result["messages"][-1].content
        return final_message


# ==================== CONVENIENCE FUNCTION ====================

def create_scrum_master_agent(
    session_id: str,
    user_id: str,
    model_name: str = "gpt-4o-mini"
) -> ScrumMasterAgent:
    """Create Scrum Master Agent instance.

    Args:
        session_id: Session ID for Langfuse tracing
        user_id: User ID for tracking
        model_name: OpenAI model name (default: gpt-4o-mini)

    Returns:
        ScrumMasterAgent instance
    """
    return ScrumMasterAgent(
        session_id=session_id,
        user_id=user_id,
        model_name=model_name
    )
