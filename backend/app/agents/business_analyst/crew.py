"""Business Analyst Crew - Requirements analysis and PRD generation."""

import json
import logging

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .tools import (
    load_prd_from_file, save_prd_to_file, update_prd_section,
    load_user_stories_from_file, save_user_stories_to_file, add_user_story,
    validate_prd_completeness, validate_user_story
)

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
            tools=[load_prd_from_file],  # Can read existing PRD for context
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
            tools=[
                load_prd_from_file,
                save_prd_to_file,
                update_prd_section,
                validate_prd_completeness
            ],  # Tools for PRD operations
            verbose=True
        )
    
    @agent
    def story_writer(self) -> Agent:
        backstory = f"""{self.persona_description}

As a Story Writer, you craft clear, actionable user stories."""
        
        return Agent(
            config=self.agents_config['story_writer'], # type: ignore[index]
            backstory=backstory,
            tools=[
                load_prd_from_file,  # Read PRD to extract stories
                load_user_stories_from_file,
                save_user_stories_to_file,
                add_user_story,
                validate_user_story
            ],  # Tools for story operations
            verbose=True
        )
    
    @agent
    def workflow_orchestrator(self) -> Agent:
        backstory = f"""{self.persona_description}

As the Workflow Orchestrator, you are the manager of a specialized BA team.
You coordinate requirements_engineer, domain_expert, prd_specialist, and story_writer
to deliver high-quality requirements analysis and documentation."""
        
        return Agent(
            config=self.agents_config['workflow_orchestrator'], # type: ignore[index]
            backstory=backstory,
            allow_delegation=True,  # Enable delegation to team members
            verbose=True
        )
    
    @task
    def complete_ba_workflow_task(self) -> Task:
        """Main task for BA workflow - manager will delegate internally."""
        return Task(
            config=self.tasks_config['complete_ba_workflow'],  # type: ignore[index]
            agent=self.workflow_orchestrator()
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates hierarchical BA crew with workflow_orchestrator as manager."""
        return Crew(
            agents=self.agents, # type: ignore[index]
            tasks=self.tasks, # type: ignore[index]
            process=Process.hierarchical,  # Hierarchical process with manager
            manager_agent=self.workflow_orchestrator(),  # Custom manager agent
            planning=True,  # Enable planning for better coordination
            verbose=True,
        )
