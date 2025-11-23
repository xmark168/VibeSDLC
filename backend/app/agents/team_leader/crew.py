"""Team Leader Crew - Multi-agent crew for project coordination."""

import logging
from typing import Dict, Any

from crewai import Agent, Crew, Task, Process
import yaml
from pathlib import Path


logger = logging.getLogger(__name__)


class TeamLeaderCrew:
    """Team Leader crew with multiple specialist agents.
    
    Crew composition:
    - Requirements Analyst: Clarifies and analyzes requirements
    - Project Coordinator: Suggests appropriate specialists
    - Progress Tracker: Monitors and reports progress
    """
    
    def __init__(self):
        """Initialize Team Leader crew."""
        self.config = self._load_config()
        self.agents = self._create_agents()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load crew configuration from YAML.
        
        Returns:
            Configuration dictionary
        """
        config_path = Path(__file__).parent / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create crew agents from configuration.
        
        Returns:
            Dictionary of agent name -> Agent instance
        """
        agents_config = self.config.get("agents", {})
        
        agents = {}
        
        # Requirements Analyst
        analyst_cfg = agents_config.get("requirements_analyst", {})
        agents["requirements_analyst"] = Agent(
            role=analyst_cfg["role"],
            goal=analyst_cfg["goal"],
            backstory=analyst_cfg["backstory"],
            verbose=True,
            allow_delegation=False,
            llm="openai/gpt-4",
        )
        
        # Project Coordinator
        coordinator_cfg = agents_config.get("project_coordinator", {})
        agents["project_coordinator"] = Agent(
            role=coordinator_cfg["role"],
            goal=coordinator_cfg["goal"],
            backstory=coordinator_cfg["backstory"],
            verbose=True,
            allow_delegation=False,
            llm="openai/gpt-4",
        )
        
        # Progress Tracker
        tracker_cfg = agents_config.get("progress_tracker", {})
        agents["progress_tracker"] = Agent(
            role=tracker_cfg["role"],
            goal=tracker_cfg["goal"],
            backstory=tracker_cfg["backstory"],
            verbose=True,
            allow_delegation=False,
            llm="openai/gpt-4",
        )
        
        logger.info(f"Created {len(agents)} agents for Team Leader crew")
        return agents
    
    def analyze_request(self, user_message: str) -> str:
        """Analyze user request and provide guidance.
        
        Uses the Requirements Analyst and Project Coordinator to:
        1. Understand what the user needs
        2. Suggest which specialist to tag
        
        Args:
            user_message: User's request message
            
        Returns:
            Analysis and guidance response
        """
        # Task 1: Analyze requirements
        analyze_task = Task(
            description=f"""Analyze this user request and identify what they need:

User Message: {user_message}

Your analysis should identify:
- What the user is asking for
- Any ambiguities that need clarification
- The type of work involved (requirements, development, testing, etc.)
""",
            agent=self.agents["requirements_analyst"],
            expected_output="Clear analysis of user needs and request type"
        )
        
        # Task 2: Respond to user naturally
        coordinate_task = Task(
            description=f"""Respond to the user's request naturally and helpfully.

User Message: {user_message}
Analysis: (from previous task)

Guidelines:
- Be friendly and concise
- For simple greetings: Respond naturally and ask how you can help
- For specific requests: Provide helpful response OR if complex/specialist needed, mention specialist naturally
- Don't lecture about tagging system
- Be conversational, not instructional

Examples:
User: "xin chào" → "Xin chào! Tôi là Victoria, Team Leader của dự án. Bạn cần giúp gì hôm nay? Tôi có thể giúp bạn với requirements, development, hoặc testing."

User: "tạo một feature login" → "Được! Feature login cần phân tích requirements trước. @BusinessAnalyst sẽ giúp bạn tạo PRD và user stories chi tiết cho feature này."

User: "kiểm tra code có bug không" → "Tôi sẽ nhờ @Tester review code và tìm bugs cho bạn."
""",
            agent=self.agents["project_coordinator"],
            expected_output="Natural, helpful response to user (not meta-explanation about tagging)",
            context=[analyze_task]
        )
        
        # Execute crew
        crew = Crew(
            agents=[
                self.agents["requirements_analyst"],
                self.agents["project_coordinator"],
            ],
            tasks=[analyze_task, coordinate_task],
            process=Process.sequential,
            verbose=True,
        )
        
        result = crew.kickoff()
        
        return str(result)
    
    def track_progress(self, project_context: str) -> str:
        """Track project progress and provide status update.
        
        Args:
            project_context: Context about current project state
            
        Returns:
            Progress status and recommendations
        """
        progress_task = Task(
            description=f"""Review the project status and provide a progress update:

Project Context: {project_context}

Provide:
- What's been completed
- What's in progress
- What's next
- Any blockers or issues
""",
            agent=self.agents["progress_tracker"],
            expected_output="Clear progress update with actionable insights"
        )
        
        crew = Crew(
            agents=[self.agents["progress_tracker"]],
            tasks=[progress_task],
            verbose=True,
        )
        
        result = crew.kickoff()
        
        return str(result)
