"""Team Leader Flow - LLM-based routing."""

import logging
from typing import Dict, Any, Optional
from crewai import Crew, Process
from crewai.flow.flow import Flow, listen, start

from app.agents.core.base_agent import TaskContext, TaskResult
from app.agents.team_leader.crew import create_routing_agent, create_routing_task

logger = logging.getLogger(__name__)


class TeamLeaderFlow(Flow):
    """Team Leader Flow: LLM decides routing."""
    
    def __init__(self, project_id: Optional[str] = None, agent_name: str = "Team Leader"):
        super().__init__()
        self.project_id = project_id
        self.agent_name = agent_name
        self.current_task: Optional[TaskContext] = None
        
        
        routing_agent = create_routing_agent()
        routing_task = create_routing_task(routing_agent)
        
        self.routing_crew = Crew(
            agents=[routing_agent],
            tasks=[routing_task],
            process=Process.sequential,
            verbose=True
        )
    
    @start()
    async def analyze_and_route(self) -> Dict[str, Any]:
        """LLM decides routing without Kanban context."""
        # Access inputs from kickoff_async(inputs={...})
        # current_task was set before kickoff
        
        # Get inputs (passed via kickoff_async)
        user_message = self.current_task.content
        user_id = str(self.current_task.user_id)
        
        context = {
            "user_message": user_message,
            "user_id": user_id,
        }
        
        result = await self.routing_crew.kickoff_async(inputs=context)
        return self._parse_routing_decision(str(result))
    
    def _parse_routing_decision(self, result_str: str) -> Dict[str, Any]:
        """Parse JSON from LLM."""
        import json
        import re
        
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', result_str, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON in output: {result_str[:200]}")
        
        routing = json.loads(json_match.group(0))
        
        if "action" not in routing or "message" not in routing:
            raise ValueError(f"Invalid routing: {routing}")
        
        return routing
    
    @listen(analyze_and_route)
    async def execute_decision(self, routing: Dict[str, Any]) -> Dict[str, Any]:
        """Return routing decision for TeamLeader to execute."""
        # Flow just returns decision, TeamLeader handles execution
        return routing
