"""Scrum Master Agent - Deep Agent coordinator.

This is the main Scrum Master agent that coordinates sprint activities.
Architecture: Deep Agent with instruction-based delegation to Sprint Planner.

Sprint Planner is an Agent-as-Tool (LangGraph workflow) because it needs
complex workflow logic that Deep Agent subagents (React-only) don't support.

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
from langfuse.langchain import CallbackHandler

from .sprint_planner.agent import SprintPlannerAgent
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

        # Initialize Langfuse callback handler
        try:
            self.langfuse_handler = CallbackHandler(
                flush_at=5,  # Flush every 5 events to avoid 413 errors
                flush_interval=1.0
            )
        except Exception:
            # Fallback for older versions without flush_at parameter
            self.langfuse_handler = CallbackHandler()

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
        def delegate_to_sprint_planner(
            po_output: dict,
            team: dict = None
        ) -> Annotated[dict, "Delegate sprint planning to Sprint Planner specialist"]:
            """Delegate complete sprint planning workflow to Sprint Planner specialist.

            Use this tool when you receive a Sprint Plan from Product Owner and need to:
            - Transform PO output to database format
            - Calculate acceptance criteria and estimates
            - Check Definition of Ready (DoR)
            - Run sprint planning workflow
            - Assign tasks to team members

            Args:
                po_output: Sprint Plan JSON from Product Owner with:
                    - metadata: Product info
                    - prioritized_backlog: List of backlog items
                    - sprints: List of sprints with assigned items
                team: Team members dict (optional, uses MOCK_TEAM by default)

            Returns:
                dict: Complete processed output with:
                    - sprints: Database-ready sprint records
                    - backlog_items: Enriched items with AC, estimates, assignments
                    - assignments: Task assignments
                    - dor_results: DoR check results
                    - summary: Statistics
            """
            try:
                print("\n" + "="*80)
                print("🎯 SCRUM MASTER: Delegating to Sprint Planner")
                print("="*80)

                # Initialize Sprint Planner
                sprint_planner = SprintPlannerAgent(
                    session_id=f"{scrum_master.session_id}_sprint_planner",
                    user_id=scrum_master.user_id,
                    model_name=scrum_master.model_name,
                    temperature=scrum_master.temperature
                )

                # Delegate complete workflow to Sprint Planner
                result = sprint_planner.process_po_output(
                    po_output=po_output,
                    team=team or MOCK_TEAM
                )

                print("\n✅ Sprint Planner delegation complete")
                return result

            except Exception as e:
                print(f"\n❌ Error delegating to Sprint Planner: {str(e)}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "error": str(e)
                }

        @tool
        def get_sprint_status(sprint_id: str) -> Annotated[dict, "Get current sprint status"]:
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
        ) -> Annotated[dict, "Update sprint task status"]:
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

        return [delegate_to_sprint_planner, get_sprint_status, update_sprint_task]

    def _create_subagents(self) -> list:
        """Create subagents for Deep Agent.

        Returns:
            List of subagent configurations (TypedDict format)
        """
        # Sprint Planner subagent config (React wrapper)
        # Note: This is a SIMPLIFIED React subagent that wraps the full LangGraph workflow
        sprint_planner_subagent = {
            "name": "sprint_planner",
            "description": "Sprint planning specialist that handles complete planning workflow from PO output to task assignments",
            "prompt": """You are the Sprint Planner specialist.

Your role: Process Product Owner output and create detailed sprint plans with task assignments.

When to activate:
- User provides Sprint Plan JSON from Product Owner
- Need to transform, enrich, and assign sprint backlog items

Your workflow:
1. Transform PO output to database format
2. Calculate acceptance criteria & estimates (LLM)
3. Check Definition of Ready (DoR)
4. Run sprint planning (daily breakdown, resource allocation)
5. Assign tasks to team members (skill-based)

You have access to the delegate_to_sprint_planner tool which runs the complete LangGraph workflow.
Use it to process the sprint plan end-to-end.

Output: Database-ready sprints, backlog items, and task assignments.""",
            "tools": ["delegate_to_sprint_planner"]
        }

        return [sprint_planner_subagent]

    def _create_agent(self):
        """Create Deep Agent with subagents, tools and instructions.

        Returns:
            Compiled deep agent
        """
        instructions = self._get_instructions()
        subagents = self._create_subagents()

        agent = create_deep_agent(
            tools=self.tools,
            instructions=instructions,
            subagents=subagents,
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
        # Build Langfuse config
        config = {
            "callbacks": [self.langfuse_handler],
            "metadata": {
                "langfuse_session_id": self.session_id,
                "langfuse_user_id": self.user_id,
                "langfuse_tags": ["scrum_master_agent"]
            }
        }

        try:
            result = self.agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ]
                },
                config=config
            )
            return result
        finally:
            # Flush Langfuse to ensure all traces are sent
            try:
                self.langfuse_handler.langfuse.flush()
            except Exception:
                pass  # Ignore flush errors

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
