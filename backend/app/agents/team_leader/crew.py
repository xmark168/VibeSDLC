"""Team Leader Crew - Multi-agent crew for project coordination."""

import logging
from typing import List

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent as CrewAIBaseAgent


logger = logging.getLogger(__name__)


@CrewBase
class TeamLeaderCrew:
    """Team Leader crew with multiple specialist agents."""
    agents: List[CrewAIBaseAgent]
    tasks: List[Task]
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @agent
    def requirements_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['requirements_analyst'],  # type: ignore[index]
            verbose=True
        )
    
    @agent
    def project_coordinator(self) -> Agent:
        return Agent(
            config=self.agents_config['project_coordinator'],  # type: ignore[index]
            verbose=True
        )
    
    @agent
    def progress_tracker(self) -> Agent:
        return Agent(
            config=self.agents_config['progress_tracker'],  # type: ignore[index]
            verbose=True
        )
    
    @task
    def analyze_requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_request']  # type: ignore[index]
        )
    
    @task
    def coordinate_response_task(self) -> Task:
        return Task(
            config=self.tasks_config['coordinate_response'],  # type: ignore[index]
            context=[self.analyze_requirements_task()]  # type: ignore[index]
        )
    
    @task
    def track_progress_task(self) -> Task:
        return Task(
            config=self.tasks_config['track_progress']  # type: ignore[index]
        )
    
    @task
    def check_delegation_task(self) -> Task:
        return Task(
            config=self.tasks_config['check_delegation']  # type: ignore[index]
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Team Leader crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
    
    async def analyze_request(self, user_message: str) -> str:
        """Analyze user request and provide guidance."""
        crew_instance = Crew(
            agents=[self.requirements_analyst(), self.project_coordinator()],
            tasks=[self.analyze_requirements_task(), self.coordinate_response_task()],
            process=Process.sequential,
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "user_message": user_message,
            "context": ""
        })
        return str(result)
    
    async def track_progress(self, project_context: str) -> str:
        """Track project progress and provide status update."""
        crew_instance = Crew(
            agents=[self.progress_tracker()],
            tasks=[self.track_progress_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "project_context": project_context,
            "context": ""
        })
        return str(result)
    
    async def check_should_delegate(self, message: str) -> tuple[bool, str]:
        """Check if message should be delegated to BA."""
        crew_instance = Crew(
            agents=[self.project_coordinator()],
            tasks=[self.check_delegation_task()],
            process=Process.sequential,
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "message": message,
            "context": ""
        })
        result_str = str(result).upper()
        
        should_delegate = "DECISION: YES" in result_str or "YES" in result_str[:100]
        reason = str(result).split("REASON:")[-1].strip() if "REASON:" in str(result) else "AI decision"
        
        return should_delegate, reason
