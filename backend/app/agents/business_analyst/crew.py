"""Business Analyst Crew - Requirements analysis and PRD generation."""

import logging

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task


logger = logging.getLogger(__name__)


@CrewBase
class BusinessAnalystCrew:
    """Business Analyst crew for requirements analysis."""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @agent
    def business_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['business_analyst'],
            verbose=True
        )
    
    @task
    def analyze_requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_requirements']
        )
    
    @task
    def check_clarification_task(self) -> Task:
        return Task(
            config=self.tasks_config['check_clarification_needed']
        )
    
    @task
    def analyze_with_context_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_with_context']
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Business Analyst crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
    
    async def analyze_requirements(self, user_message: str) -> str:
        """Analyze requirements for a user message."""
        crew_instance = Crew(
            agents=[self.business_analyst()],
            tasks=[self.analyze_requirements_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={"user_message": user_message})
        return str(result)
    
    async def check_needs_clarification(self, message: str) -> bool:
        """Check if message needs clarification."""
        crew_instance = Crew(
            agents=[self.business_analyst()],
            tasks=[self.check_clarification_task()],
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={"message": message})
        result_str = str(result).upper()
        
        needs_clarification = "DECISION: YES" in result_str or (
            "YES" in result_str[:100] and "NO" not in result_str[:50]
        )
        
        return needs_clarification
    
    async def analyze_with_context(
        self,
        original_message: str,
        selected_aspects: str,
        aspects_list: str
    ) -> str:
        """Analyze with user-selected context."""
        crew_instance = Crew(
            agents=[self.business_analyst()],
            tasks=[self.analyze_with_context_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "original_message": original_message,
            "selected_aspects": selected_aspects,
            "aspects_list": aspects_list
        })
        return str(result)
