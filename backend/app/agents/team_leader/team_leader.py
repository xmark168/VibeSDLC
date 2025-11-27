"""
Team Leader Agent - CrewAI-based Kanban Flow Orchestration

Following CrewAI best practices:
- ONE crew handles entire workflow
- Sequential task execution with automatic context passing
- LLM-based routing decisions (no hardcoded rules)
"""

import json
import logging
import re

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.team_leader.crew import TeamLeaderCrew
from app.agents.team_leader.kanban_state import KanbanStateManager
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


# Language instruction for Vietnamese responses
VIETNAMESE_RESPONSE_INSTRUCTION = """
CRITICAL LANGUAGE REQUIREMENT:
- You MUST respond to users in Vietnamese (Tiếng Việt)
- Write naturally and conversationally, as if talking to a Vietnamese colleague
- Be friendly, professional, and helpful
- Use Vietnamese terminology for roles:
  * Business Analyst → "Chuyên viên Phân tích" or "BA"
  * Developer → "Lập trình viên" or "Dev"
  * Tester → "Kiểm thử viên" or "QA"
  * Team Leader → "Trưởng nhóm"
- Explain technical terms naturally when needed
- Keep responses concise (4-5 sentences max unless providing detailed status)
"""


class TeamLeader(BaseAgent):
    """Team Leader agent - coordinates project activities using CrewAI.

    Architecture (CrewAI-compliant):
    - ONE crew orchestrates entire workflow via sequential tasks
    - Kanban context feeds into LLM decision-making
    - No hardcoded routing rules - LLM decides based on board state
    
    Workflow:
    1. User message arrives → gather Kanban context
    2. Kickoff ONE crew (4 sequential tasks):
       - Task 1: Analyze Kanban context + user intent
       - Task 2: Classify intent category
       - Task 3: Make routing decision (with WIP checks)
       - Task 4: Generate natural response
    3. Parse crew output → delegate or respond
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Team Leader with unified crew."""
        super().__init__(agent_model, **kwargs)

        # Initialize THE crew (not multiple mini-crews!)
        self.crew = TeamLeaderCrew()
        
        # Initialize Kanban state manager for context
        self.kanban = None
        if self.project_id:
            from app.core.db import engine
            from sqlmodel import Session
            with Session(engine) as session:
                self.kanban = KanbanStateManager(self.project_id, session)

        logger.info(f"Team Leader initialized: {self.name} (CrewAI unified workflow)")

    async def _get_kanban_context(self) -> dict:
        """Get Kanban board context for crew inputs.
        
        Returns:
            Flattened context dict that can be spread into crew inputs
        """
        if not self.kanban:
            return {
                # Language directives for Vietnamese responses
                "response_language": "Vietnamese",
                "language_instruction": VIETNAMESE_RESPONSE_INSTRUCTION,
                
                # Default Kanban context (no board available)
                "backlog_count": 0,
                "todo_count": 0,
                "in_progress_current": 0,
                "in_progress_limit": 5,
                "in_progress_wip_pct": 0,
                "review_current": 0,
                "review_limit": 3,
                "review_wip_pct": 0,
                "done_count": 0,
                "cycle_time": 0,
                "throughput": 0,
                "bottlenecks": "None",
                "board_snapshot": "{}",
                "wip_status": "{}",
                "flow_metrics": "{}",
                "epics_progress": "{}",
            }
        
        # Gather rich Kanban data
        board = self.kanban.get_board_snapshot()
        wip_status = self.kanban.get_wip_status()
        bottlenecks = self.kanban.detect_bottlenecks()
        flow_metrics = await self.kanban.get_flow_metrics()
        epics = self.kanban.get_all_epics_progress()
        
        # Flatten for easy template variable substitution
        return {
            # Language directives for Vietnamese responses
            "response_language": "Vietnamese",
            "language_instruction": VIETNAMESE_RESPONSE_INSTRUCTION,
            
            # Column counts
            "backlog_count": len(board.get("Backlog", [])),
            "todo_count": len(board.get("Todo", [])),
            "in_progress_current": len(board.get("InProgress", [])),
            "in_progress_limit": wip_status.get("InProgress", {}).get("limit", 5),
            "in_progress_wip_pct": round(wip_status.get("InProgress", {}).get("utilization", 0) * 100, 1),
            "review_current": len(board.get("Review", [])),
            "review_limit": wip_status.get("Review", {}).get("limit", 3),
            "review_wip_pct": round(wip_status.get("Review", {}).get("utilization", 0) * 100, 1),
            "done_count": len(board.get("Done", [])),
            
            # Flow metrics
            "cycle_time": round(flow_metrics.get("avg_cycle_time_hours", 0) / 24, 1),
            "throughput": flow_metrics.get("throughput_per_week", 0),
            
            # Structured data (for context passing)
            "bottlenecks": json.dumps(bottlenecks) if bottlenecks else "None",
            "board_snapshot": json.dumps(board),
            "wip_status": json.dumps(wip_status),
            "flow_metrics": json.dumps(flow_metrics),
            "epics_progress": json.dumps(epics) if epics else "{}",
        }
    
    def _parse_routing_from_crew_output(self, crew_output: str) -> dict:
        """Parse routing decision from crew's final output.
        
        The generate_response task should output natural language, but we need
        to extract the routing decision from the route_decision task context.
        
        Look for JSON in crew output or parse structured format.
        """
        output_str = str(crew_output)
        
        # Try to find JSON in output
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', output_str, re.DOTALL)
        if json_match:
            try:
                routing = json.loads(json_match.group(0))
                return routing
            except json.JSONDecodeError:
                pass
        
        # Fallback: Parse key-value format
        routing = {
            "action": "HANDLE_DIRECTLY",
            "agent": "team_leader",
            "reason": "Default handling",
            "response": output_str
        }
        
        # Try to extract action
        if "DELEGATE" in output_str.upper():
            routing["action"] = "DELEGATE"
        
        # Try to extract agent
        for agent_name in ["business_analyst", "developer", "tester"]:
            if agent_name in output_str.lower() or agent_name.replace("_", " ") in output_str.lower():
                routing["agent"] = agent_name
                break
        
        return routing

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using ONE unified crew kickoff."""
        try:
            user_message = task.content
            task_type = task.task_type.value

            logger.info(f"[{self.name}] Processing {task_type}: {user_message[:50]}...")

            # Handle delegation_failed callback
            if task.context.get("delegation_failed"):
                target_role = task.context.get("target_role")
                error_message = task.context.get("error_message")
                
                logger.warning(f"[{self.name}] Delegation to {target_role} failed, providing fallback")
                
                fallback_response = (
                    f"{error_message}\n\n"
                    f"However, I can help you with:\n"
                    f"- Explaining how to start a new project\n"
                    f"- Guiding through development process\n"
                    f"- Answering general questions\n\n"
                    f"What can I help you with?"
                )
                
                return TaskResult(
                    success=True,
                    output=fallback_response,
                    structured_data={"delegation_failed": True, "fallback_provided": True}
                )
            
            # Step 1: Gather Kanban context
            kanban_ctx = await self._get_kanban_context()
            logger.info(
                f"[{self.name}] Kanban context: InProgress {kanban_ctx['in_progress_current']}/"
                f"{kanban_ctx['in_progress_limit']}, Review {kanban_ctx['review_current']}/"
                f"{kanban_ctx['review_limit']}"
            )
            
            # Step 2: Prepare inputs for crew (combines message + context)
            inputs = {
                "user_message": user_message,
                "user_id": str(task.user_id),
                **kanban_ctx  # Spread all Kanban context for task templates
            }
            
            # Step 3: ONE CREW KICKOFF - CrewAI handles everything!
            logger.info(f"[{self.name}] Kicking off unified crew workflow...")
            crew_result = await self.crew.crew().kickoff_async(inputs=inputs)
            
            logger.info(f"[{self.name}] Crew completed successfully")
            
            # Step 4: Parse crew output
            crew_output = str(crew_result) if crew_result else ""
            routing = self._parse_routing_from_crew_output(crew_output)
            
            logger.info(
                f"[{self.name}] Routing decision: {routing['action']} → {routing['agent']}"
            )
            
            # Step 5: Act on routing decision
            if routing["action"] == "DELEGATE" and routing["agent"] != "team_leader":
                # Mark delegation
                from datetime import datetime, timezone
                task.context["delegation_attempted"] = True
                task.context["delegation_timestamp"] = datetime.now(timezone.utc).isoformat()
                task.context["routing_reason"] = routing.get("reason", "Crew routing decision")
                
                # Delegate to specialist
                return await self.delegate_to_role(
                    task=task,
                    target_role=routing["agent"],
                    delegation_message=f"Routed by Team Leader crew: {routing.get('reason', 'See context')}"
                )
            
            # Team Leader handles directly - use crew's response
            response = routing.get("response", crew_output)
            
            # Sanity checks
            if not response or not response.strip():
                logger.warning(f"[{self.name}] Empty response from crew, using fallback")
                response = (
                    f"I've analyzed your request about: {user_message[:50]}...\n\n"
                    f"I can help coordinate this work. Could you provide more details?"
                )
            
            if len(response) > 5000:
                logger.warning(f"[{self.name}] Response too long, truncating")
                response = response[:5000] + "\n\n... (message truncated)"
            
            return TaskResult(
                success=True,
                output=response,
                structured_data={
                    "routing_decision": routing,
                    "kanban_context": kanban_ctx,
                    "crew_workflow": "unified",
                },
                requires_approval=False,
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Team Leader error: {str(e)}",
            )
