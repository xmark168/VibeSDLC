"""Scrum Master Agent - Supervisor Agent with routing.

This is the main Scrum Master agent that coordinates sprint activities.
Architecture: Supervisor Agent that routes to appropriate sub-agents using LangGraph.

Supported Events:
- sprint_planning: Delegates to SprintPlannerAgent
- daily_scrum: Delegates to DailyScrumAgent (future)
- sprint_review: Delegates to SprintReviewAgent (future)
- sprint_retrospective: Delegates to RetrospectiveAgent (future)

DRAFT VERSION - No database connection, uses hardcoded test data.
Output format matches database schema for future integration.
"""

import os
import sys
import json
from typing import Optional, Literal, TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END
from langfuse.langchain import CallbackHandler

# Fix import for running as script
if __name__ == "__main__":
    # Add current directory to path for imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    from sprint_planner.agent import SprintPlannerAgent
    from models import ScrumMasterOutput
    from test_data import MOCK_TEAM
else:
    from .sprint_planner.agent import SprintPlannerAgent
    from .models import ScrumMasterOutput
    from .test_data import MOCK_TEAM


# ==================== STATE ====================

class ScrumMasterState(TypedDict):
    """State for Scrum Master Supervisor Agent."""
    event_type: str  # sprint_planning, daily_scrum, sprint_review, sprint_retrospective
    input_data: dict  # Input data (po_output, daily_updates, etc.)
    team: dict  # Team members
    result: dict  # Final result
    error: Optional[str]  # Error message if any


# ==================== SCRUM MASTER AGENT ====================

class ScrumMasterAgent:
    """Scrum Master Agent - Supervisor Agent with routing to sub-agents."""

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

        # Initialize Langfuse callback handler
        try:
            self.langfuse_handler = CallbackHandler(
                flush_at=5,  # Flush every 5 events to avoid 413 errors
                flush_interval=1.0
            )
        except Exception:
            # Fallback for older versions without flush_at parameter
            self.langfuse_handler = CallbackHandler()

        # Initialize sub-agents
        self.sprint_planner = SprintPlannerAgent(
            session_id=f"{session_id}_sprint_planner",
            user_id=user_id,
            model_name=model_name,
            temperature=temperature
        )
        # Future sub-agents:
        # self.daily_scrum_agent = DailyScrumAgent(...)
        # self.retrospective_agent = RetrospectiveAgent(...)

        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow with router and delegate nodes.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(ScrumMasterState)

        # Add nodes
        workflow.add_node("router", self._router_node)
        workflow.add_node("sprint_planning", self._sprint_planning_node)
        workflow.add_node("daily_scrum", self._daily_scrum_node)
        workflow.add_node("sprint_review", self._sprint_review_node)
        workflow.add_node("sprint_retrospective", self._retrospective_node)
        workflow.add_node("finalize", self._finalize_node)

        # Set entry point
        workflow.set_entry_point("router")

        # Add conditional edges from router
        workflow.add_conditional_edges(
            "router",
            self._route_to_subagent,
            {
                "sprint_planning": "sprint_planning",
                "daily_scrum": "daily_scrum",
                "sprint_review": "sprint_review",
                "sprint_retrospective": "sprint_retrospective",
                "error": "finalize"
            }
        )

        # Add edges from sub-agents to finalize
        workflow.add_edge("sprint_planning", "finalize")
        workflow.add_edge("daily_scrum", "finalize")
        workflow.add_edge("sprint_review", "finalize")
        workflow.add_edge("sprint_retrospective", "finalize")

        # Add edge from finalize to END
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _router_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Router node: Validate event_type and prepare for routing."""
        print("\n" + "="*80)
        print(f"🎯 SCRUM MASTER ROUTER: Event type = {state['event_type']}")
        print("="*80)

        valid_events = ["sprint_planning", "daily_scrum", "sprint_review", "sprint_retrospective"]
        if state["event_type"] not in valid_events:
            state["error"] = f"Invalid event_type: {state['event_type']}. Must be one of {valid_events}"
            print(f"❌ {state['error']}")

        return state

    def _route_to_subagent(self, state: ScrumMasterState) -> Literal["sprint_planning", "daily_scrum", "sprint_review", "sprint_retrospective", "error"]:
        """Conditional edge: Route to appropriate sub-agent based on event_type."""
        if state.get("error"):
            return "error"
        return state["event_type"]

    def _sprint_planning_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Delegate to Sprint Planner Agent."""
        print("\n🔄 Delegating to Sprint Planner Agent...")
        try:
            # Extract data from input_data
            # input_data should contain: {sprint_info, backlog_items}
            input_data = state["input_data"]
            sprint_info = input_data.get("sprint_info", {})
            backlog_items = input_data.get("backlog_items", [])

            # Filter backlog items by assigned_items in sprint
            assigned_item_ids = sprint_info.get("assigned_items", [])
            sprint_backlog_items = [
                item for item in backlog_items
                if item.get("id") in assigned_item_ids
            ]

            print(f"   - Sprint: {sprint_info.get('sprint_id')}")
            print(f"   - Assigned items: {len(assigned_item_ids)}")
            print(f"   - Filtered backlog items: {len(sprint_backlog_items)}")

            # Calculate sprint duration
            from datetime import datetime
            start_date = datetime.fromisoformat(sprint_info.get("start_date", "2025-01-01"))
            end_date = datetime.fromisoformat(sprint_info.get("end_date", "2025-01-15"))
            duration_days = (end_date - start_date).days

            # Run Sprint Planner
            result = self.sprint_planner.run(
                sprint_id=sprint_info.get("sprint_id", "sprint-1"),
                sprint_number=sprint_info.get("sprint_number", 1),
                sprint_goal=sprint_info.get("sprint_goal", ""),
                start_date=sprint_info.get("start_date", ""),
                end_date=sprint_info.get("end_date", ""),
                sprint_duration_days=duration_days,
                velocity_plan=sprint_info.get("velocity_plan", 0),
                sprint_backlog_items=sprint_backlog_items,
                team_capacity=state["team"].get("capacity", {"dev_hours": 80, "qa_hours": 40}),
                team_members=state["team"].get("members", [])
            )

            state["result"] = result
        except Exception as e:
            state["error"] = f"Sprint Planning error: {str(e)}"
            print(f"❌ {state['error']}")
            import traceback
            traceback.print_exc()
        return state

    def _daily_scrum_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Delegate to Daily Scrum Agent (placeholder)."""
        print("\n🔄 Delegating to Daily Scrum Agent...")
        # TODO: Implement DailyScrumAgent with run() method
        # result = self.daily_scrum_agent.run(...)
        state["result"] = {
            "success": False,
            "message": "Daily Scrum Agent not implemented yet"
        }
        return state

    def _sprint_review_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Delegate to Sprint Review Agent (placeholder)."""
        print("\n🔄 Delegating to Sprint Review Agent...")
        # TODO: Implement SprintReviewAgent with run() method
        # result = self.sprint_review_agent.run(...)
        state["result"] = {
            "success": False,
            "message": "Sprint Review Agent not implemented yet"
        }
        return state

    def _retrospective_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Delegate to Retrospective Agent (placeholder)."""
        print("\n🔄 Delegating to Retrospective Agent...")
        # TODO: Implement RetrospectiveAgent with run() method
        # result = self.retrospective_agent.run(...)
        state["result"] = {
            "success": False,
            "message": "Retrospective Agent not implemented yet"
        }
        return state

    def _finalize_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Finalize and return result."""
        if state.get("error"):
            state["result"] = {
                "success": False,
                "error": state["error"]
            }
        print("\n✅ SCRUM MASTER: Processing complete")
        return state

    def process_event(
        self,
        event_type: str,
        input_data: dict,
        team: Optional[dict] = None
    ) -> dict:
        """Process scrum event by routing to appropriate sub-agent.

        Args:
            event_type: Type of scrum event (sprint_planning, daily_scrum, etc.)
            input_data: Input data for the event
            team: Team members dict (optional, uses MOCK_TEAM by default)

        Returns:
            dict: Result from sub-agent
        """
        try:
            # Prepare initial state
            initial_state: ScrumMasterState = {
                "event_type": event_type,
                "input_data": input_data,
                "team": team or MOCK_TEAM,
                "result": {},
                "error": None
            }

            # Run graph
            final_state = self.graph.invoke(initial_state)

            return final_state["result"]

        except Exception as e:
            print(f"\n❌ SCRUM MASTER: Error processing event: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Flush Langfuse traces
            try:
                self.langfuse_handler.langfuse.flush()
            except Exception:
                pass

    def process_po_output(
        self,
        po_output: dict,
        team: Optional[dict] = None
    ) -> dict:
        """Process Product Owner output through Sprint Planner.

        Convenience method for backward compatibility.

        Args:
            po_output: PO output with metadata, prioritized_backlog, sprints
            team: Team members dict (optional, uses MOCK_TEAM by default)

        Returns:
            dict: Complete processed output with sprints, items, assignments
        """
        return self.process_event(
            event_type="sprint_planning",
            input_data=po_output,
            team=team
        )






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


# ==================== TEST ====================

if __name__ == "__main__":
    """Test Scrum Master Agent with backlog.json and sprint.json."""

    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Check required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not set in environment variables")
        print("Please set OPENAI_API_KEY in .env file or environment")
        sys.exit(1)

    print("\n" + "="*80)
    print("🧪 TESTING SCRUM MASTER AGENT")
    print("="*80)

    # Load test data from files
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Load backlog.json
    backlog_file = os.path.join(current_dir, "backlog.json")
    with open(backlog_file, "r", encoding="utf-8") as f:
        backlog_items = json.load(f)
    print(f"\n✅ Loaded {len(backlog_items)} backlog items from backlog.json")

    # Load sprint.json
    sprint_file = os.path.join(current_dir, "sprint.json")
    with open(sprint_file, "r", encoding="utf-8") as f:
        sprints = json.load(f)
    print(f"✅ Loaded {len(sprints)} sprint(s) from sprint.json")

    # Get first sprint
    sprint_info = sprints[0]
    print(f"\n📋 Sprint Info:")
    print(f"   - Sprint ID: {sprint_info.get('sprint_id')}")
    print(f"   - Sprint Goal: {sprint_info.get('sprint_goal')}")
    print(f"   - Duration: {sprint_info.get('start_date')} to {sprint_info.get('end_date')}")
    print(f"   - Velocity Plan: {sprint_info.get('velocity_plan')}")
    print(f"   - Assigned Items: {len(sprint_info.get('assigned_items', []))}")

    # Prepare input data for Scrum Master
    input_data = {
        "sprint_info": sprint_info,
        "backlog_items": backlog_items
    }

    # Create team info
    team = {
        "capacity": {
            "dev_hours": 160,  # 2 devs * 80 hours
            "qa_hours": 80,    # 1 QA * 80 hours
            "design_hours": 40  # 0.5 designer * 80 hours
        },
        "members": [
            {"name": "Alice", "role": "Developer", "capacity_hours": 80},
            {"name": "Bob", "role": "Developer", "capacity_hours": 80},
            {"name": "Charlie", "role": "Tester", "capacity_hours": 80},
            {"name": "Diana", "role": "Designer", "capacity_hours": 40}
        ]
    }

    # Create Scrum Master Agent
    print("\n👔 Creating Scrum Master Agent...")
    scrum_master = create_scrum_master_agent(
        session_id="test_session_001",
        user_id="test_user",
        model_name="gpt-4o-mini"
    )

    # Test Sprint Planning
    print("\n🚀 Testing Sprint Planning...")
    result = scrum_master.process_event(
        event_type="sprint_planning",
        input_data=input_data,
        team=team
    )

    # Display results
    print("\n" + "="*80)
    print("📊 RESULTS")
    print("="*80)

    if result.get("success") is False or result.get("error"):
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
    else:
        print(f"\n✅ Status: {result.get('status', 'N/A')}")
        print(f"✅ Plan Score: {result.get('plan_score', 0.0):.2f}")

        sprint_plan = result.get("sprint_plan", {})
        enriched_items = result.get("enriched_items", [])
        task_assignments = result.get("task_assignments", [])

        print(f"\n📋 Sprint Plan:")
        print(f"   - Enriched Items: {len(enriched_items)}")
        print(f"   - Task Assignments: {len(task_assignments)}")

        resource_allocation = result.get("resource_allocation", {})
        print(f"\n👥 Resource Allocation:")
        for key, value in resource_allocation.items():
            print(f"   - {key}: {value}")

        daily_breakdown = result.get("daily_breakdown", [])
        print(f"\n📅 Daily Breakdown: {len(daily_breakdown)} days")

        # Export to JSON
        print("\n📝 Exporting to JSON...")

        # Create comprehensive report
        report = {
            "sprint_info": {
                "sprint_id": sprint_info.get("sprint_id"),
                "sprint_number": sprint_info.get("sprint_number"),
                "sprint_goal": sprint_info.get("sprint_goal"),
                "start_date": sprint_info.get("start_date"),
                "end_date": sprint_info.get("end_date"),
                "velocity_plan": sprint_info.get("velocity_plan"),
                "assigned_items_count": len(sprint_info.get("assigned_items", []))
            },
            "planning_summary": {
                "status": result.get("status"),
                "plan_score": result.get("plan_score"),
                "total_enriched_items": len(enriched_items),
                "total_task_assignments": len(task_assignments),
                "total_days": len(daily_breakdown)
            },
            "resource_allocation": resource_allocation,
            "enriched_items": enriched_items,
            "task_assignments": task_assignments,
            "daily_breakdown": daily_breakdown,
            "full_result": result
        }

        output_file = os.path.join(current_dir, "sprint_planning_report.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ Exported to: {output_file}")

        # Print summary
        print(f"\n📊 Report Summary:")
        print(f"   - Total Backlog Items: {len(backlog_items)}")
        print(f"   - Assigned Items: {len(sprint_info.get('assigned_items', []))}")
        print(f"   - Enriched Items: {len(enriched_items)}")
        print(f"   - Enrichment Rate: {len(enriched_items)}/{len(sprint_info.get('assigned_items', []))} ({100*len(enriched_items)/max(1, len(sprint_info.get('assigned_items', []))):.1f}%)")

    print("\n" + "="*80)
    print("✅ TEST COMPLETED")
    print("="*80 + "\n")
