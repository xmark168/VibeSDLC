"""Scrum Master Agent - Supervisor Agent with routing.

This is the main Scrum Master agent that coordinates sprint activities.
Architecture: Supervisor Agent that routes to appropriate sub-agents using LangGraph.

Supported Events:
- daily_scrum: Delegates to DailyCoordinatorAgent
- sprint_retrospective: Delegates to RetroCoordinatorAgent

Note: Sprint Planning is now handled by Product Owner Agent.
      Developer/Tester Agents access Knowledge Base directly when executing tasks.
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

    from daily_coodinator.agent import DailyCoordinatorAgent
    from retro_coordinator.agent import RetroCoordinatorAgent
    from test_data import MOCK_TEAM
else:
    from .daily_coodinator.agent import DailyCoordinatorAgent
    from .retro_coordinator.agent import RetroCoordinatorAgent
    from .test_data import MOCK_TEAM


# ==================== STATE ====================

class ScrumMasterState(TypedDict):
    """State for Scrum Master Supervisor Agent."""
    event_type: str  # daily_scrum, sprint_retrospective
    input_data: dict  # Input data (sprint_id, date, etc.)
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
        self.daily_coordinator = DailyCoordinatorAgent(
            session_id=f"{session_id}_daily_coordinator",
            user_id=user_id
        )
        self.retro_coordinator = RetroCoordinatorAgent(
            session_id=f"{session_id}_retro_coordinator",
            user_id=user_id
        )

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
        workflow.add_node("daily_scrum", self._daily_scrum_node)
        workflow.add_node("sprint_retrospective", self._retrospective_node)
        workflow.add_node("finalize", self._finalize_node)

        # Set entry point
        workflow.set_entry_point("router")

        # Add conditional edges from router
        workflow.add_conditional_edges(
            "router",
            self._route_to_subagent,
            {
                "daily_scrum": "daily_scrum",
                "sprint_retrospective": "sprint_retrospective",
                "error": "finalize"
            }
        )

        # Add edges from sub-agents to finalize
        workflow.add_edge("daily_scrum", "finalize")
        workflow.add_edge("sprint_retrospective", "finalize")

        # Add edge from finalize to END
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _router_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Router node: Validate event_type and prepare for routing."""
        print("\n" + "="*80)
        print(f"🎯 SCRUM MASTER ROUTER: Event type = {state['event_type']}")
        print("="*80)

        valid_events = ["daily_scrum", "sprint_retrospective"]
        if state["event_type"] not in valid_events:
            state["error"] = f"Invalid event_type: {state['event_type']}. Must be one of {valid_events}"
            print(f"❌ {state['error']}")

        return state

    def _route_to_subagent(self, state: ScrumMasterState) -> Literal["daily_scrum", "sprint_retrospective", "error"]:
        """Conditional edge: Route to appropriate sub-agent based on event_type."""
        if state.get("error"):
            return "error"
        return state["event_type"]



    def _daily_scrum_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Delegate to Daily Coordinator Agent."""
        print("\n🔄 Delegating to Daily Coordinator Agent...")
        try:
            # Extract data from input_data
            input_data = state["input_data"]
            sprint_id = input_data.get("sprint_id", "sprint-1")
            date = input_data.get("date")

            print(f"   - Sprint: {sprint_id}")
            if date:
                print(f"   - Date: {date}")

            # Run Daily Coordinator
            result = self.daily_coordinator.run(
                sprint_id=sprint_id,
                date=date
            )

            state["result"] = result
        except Exception as e:
            state["error"] = f"Daily Scrum error: {str(e)}"
            print(f"❌ {state['error']}")
            import traceback
            traceback.print_exc()
        return state

    def _retrospective_node(self, state: ScrumMasterState) -> ScrumMasterState:
        """Delegate to Retro Coordinator Agent."""
        print("\n🔄 Delegating to Retro Coordinator Agent...")
        try:
            # Extract data from input_data
            input_data = state["input_data"]
            sprint_id = input_data.get("sprint_id", "sprint-1")
            sprint_name = input_data.get("sprint_name", "Sprint 1")
            project_id = input_data.get("project_id", "project-001")
            date = input_data.get("date")

            print(f"   - Sprint: {sprint_id}")
            print(f"   - Sprint Name: {sprint_name}")
            if date:
                print(f"   - Date: {date}")

            # Run Retro Coordinator
            result = self.retro_coordinator.run(
                sprint_id=sprint_id,
                sprint_name=sprint_name,
                project_id=project_id,
                date=date
            )

            state["result"] = result
        except Exception as e:
            state["error"] = f"Sprint Retrospective error: {str(e)}"
            print(f"❌ {state['error']}")
            import traceback
            traceback.print_exc()
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

    async def persist_sprint_plan(
        self,
        sprint_plan_data: dict,
        project_id: str,
        websocket_broadcast_fn
    ) -> dict:
        """Persist sprint plan to database.

        This method is called by auto-trigger flow after user approves sprint plan.
        It uses ScrumMasterOrchestrator to persist sprint plan and backlog items to database.

        Args:
            sprint_plan_data: Sprint plan data from Priority Agent (structured_data from message)
            project_id: Project ID
            websocket_broadcast_fn: Async function to broadcast messages

        Returns:
            dict: Result with saved sprint and item IDs
        """
        print(f"\n[ScrumMasterAgent.persist_sprint_plan] ENTERED", flush=True)
        print(f"[ScrumMasterAgent.persist_sprint_plan] project_id: {project_id}", flush=True)

        try:
            # Import orchestrator
            from .orchestrator import ScrumMasterOrchestrator

            # Extract sprint plan and backlog items from structured data
            sprint_plan = sprint_plan_data
            backlog_items = sprint_plan_data.get("prioritized_backlog", [])

            print(f"[ScrumMasterAgent] Sprint Plan: {len(sprint_plan.get('sprints', []))} sprints")
            print(f"[ScrumMasterAgent] Backlog Items: {len(backlog_items)} items")

            # Create orchestrator
            orchestrator = ScrumMasterOrchestrator(
                project_id=project_id,
                user_id=self.user_id,
                session_id=self.session_id,
                websocket_broadcast_fn=websocket_broadcast_fn
            )

            # Process sprint plan and persist to database
            result = await orchestrator.process_po_output(
                sprint_plan=sprint_plan,
                backlog_items=backlog_items
            )

            print(f"[ScrumMasterAgent] Orchestrator completed: {result.get('total_sprints', 0)} sprints, {result.get('total_items', 0)} items")

            return {
                "status": "success",
                "total_sprints": result.get("total_sprints", 0),
                "total_items": result.get("total_items", 0),
                "saved_sprint_ids": result.get("saved_sprint_ids", []),
                "saved_item_ids": result.get("saved_item_ids", [])
            }

        except Exception as e:
            print(f"[ScrumMasterAgent] Error persisting sprint plan: {e}")
            import traceback
            traceback.print_exc()

            # Broadcast error
            await websocket_broadcast_fn({
                "type": "agent_step",
                "step": "error",
                "agent": "Scrum Master",
                "message": f"❌ Lỗi khi lưu Sprint Plan: {str(e)}"
            }, project_id)

            return {
                "status": "error",
                "error": str(e)
            }








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
    """Test Scrum Master Agent - Daily Scrum and Retrospective."""

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

    # Create Scrum Master Agent
    print("\n👔 Creating Scrum Master Agent...")
    scrum_master = create_scrum_master_agent(
        session_id="test_session_001",
        user_id="test_user",
        model_name="gpt-4o-mini"
    )

    # Test 1: Daily Scrum
    print("\n" + "="*80)
    print("🚀 TEST 1: DAILY SCRUM")
    print("="*80)

    daily_input = {
        "sprint_id": "sprint-1",
        "date": "2025-01-15"
    }

    result = scrum_master.process_event(
        event_type="daily_scrum",
        input_data=daily_input
    )

    print("\n📊 Daily Scrum Results:")
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Status: {result.get('status', 'N/A')}")
        print(f"✅ Summary: {result.get('daily_summary', {}).get('summary', 'N/A')}")

    # Test 2: Sprint Retrospective
    print("\n" + "="*80)
    print("🚀 TEST 2: SPRINT RETROSPECTIVE")
    print("="*80)

    retro_input = {
        "sprint_id": "sprint-1",
        "sprint_name": "Sprint 1 - Foundation",
        "project_id": "project-001",
        "date": "2025-01-20"
    }

    result = scrum_master.process_event(
        event_type="sprint_retrospective",
        input_data=retro_input
    )

    print("\n📊 Retrospective Results:")
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Status: {result.get('status', 'N/A')}")
        retro_summary = result.get('retro_summary', {})
        print(f"✅ Total Issues: {retro_summary.get('total_issues', 0)}")
        print(f"✅ Total Ideas: {retro_summary.get('total_ideas', 0)}")
        print(f"✅ Total Actions: {retro_summary.get('total_actions', 0)}")
        print(f"✅ Total Rules: {retro_summary.get('total_rules', 0)}")

    print("\n" + "="*80)
    print("✅ TEST COMPLETED")
    print("="*80 + "\n")
