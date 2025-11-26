"""Business Analyst Crew - Requirements analysis and PRD generation."""

import json
import logging

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


logger = logging.getLogger(__name__)


@CrewBase
class BusinessAnalystCrew:
    """Multi-agent BA crew with specialized sub-agents."""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(
        self,
        agent_name: str = "Business Analyst",
        personality_traits: list[str] | None = None,
        communication_style: str | None = None
    ):
        self.agent_name = agent_name
        self.personality_traits = personality_traits or []
        self.communication_style = communication_style or "professional and clear"
        
        self.persona_description = self._build_persona_description()
    
    def _build_persona_description(self) -> str:
        traits_str = ", ".join(self.personality_traits) if self.personality_traits else "professional"
        
        return f"""You are {self.agent_name}, a Business Analyst.

Personality Traits: {traits_str}
Communication Style: {self.communication_style}

Embody this personality in all responses while maintaining professionalism."""
    
    @agent
    def requirements_engineer(self) -> Agent:  
        backstory = f"""{self.persona_description} As a Requirements Engineer, you excel at asking targeted clarification questions and detecting missing information."""
        return Agent(
            config=self.agents_config['requirements_engineer'], # type: ignore[index]
            backstory=backstory,
            verbose=True
        )
    
    @agent
    def domain_expert(self) -> Agent:
        backstory = f"""{self.persona_description}

As a Domain Expert, you analyze business context and explain complex domain concepts clearly."""
        
        return Agent(
            config=self.agents_config['domain_expert'], # type: ignore[index]
            backstory=backstory,
            verbose=True
        )
    
    @agent
    def prd_specialist(self) -> Agent:
        backstory = f"""{self.persona_description}

As a PRD Specialist, you create clear and comprehensive documentation."""
        
        return Agent(
            config=self.agents_config['prd_specialist'], # type: ignore[index]
            backstory=backstory,
            verbose=True
        )
    
    @agent
    def story_writer(self) -> Agent:
        backstory = f"""{self.persona_description}

As a Story Writer, you craft clear, actionable user stories."""
        
        return Agent(
            config=self.agents_config['story_writer'], # type: ignore[index]
            backstory=backstory,
            verbose=True
        )
    
    @agent
    def workflow_orchestrator(self) -> Agent:
        backstory = f"""{self.persona_description}

As the Workflow Orchestrator, you coordinate your team of specialists and make intelligent routing decisions."""
        
        return Agent(
            config=self.agents_config['workflow_orchestrator'], # type: ignore[index]
            backstory=backstory,
            verbose=True
        )
    
    @task
    def analyze_requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_requirements']  # type: ignore[index]
        )
    
    @task
    def check_clarification_task(self) -> Task:
        return Task(
            config=self.tasks_config['check_clarification_needed']  # type: ignore[index]
        )
    
    @task
    def analyze_with_context_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_with_context']  # type: ignore[index]
        )
    
    @task
    def detect_intent_task(self) -> Task:
        return Task(
            config=self.tasks_config['detect_intent']  # type: ignore[index]
        )
    
    @task
    def generate_interview_question_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_interview_question']  # type: ignore[index]
        )
    
    @task
    def generate_prd_from_interview_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_prd_from_interview']  # type: ignore[index]
        )
    
    @task
    def extract_user_stories_task(self) -> Task:
        return Task(
            config=self.tasks_config['extract_user_stories_from_prd']  # type: ignore[index]
        )
    
    @task
    def update_existing_prd_task(self) -> Task:
        return Task(
            config=self.tasks_config['update_existing_prd']  # type: ignore[index]
        )
    
    @task
    def generate_first_clarification_question_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_first_clarification_question']  # type: ignore[index]
        )
    
    @task
    def generate_next_interview_question_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_next_interview_question']  # type: ignore[index]
        )
    
    @task
    def decide_next_action_task(self) -> Task:
        return Task(
            config=self.tasks_config['decide_next_action']  # type: ignore[index]
        )
    
    @task
    def analyze_and_route_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_and_route']  # type: ignore[index]
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Business Analyst crew."""
        return Crew(
            agents=self.agents, # type: ignore[index]
            tasks=self.tasks, # type: ignore[index]
            process=Process.sequential,
            verbose=True,
        )
