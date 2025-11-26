"""Business Analyst Crew - Requirements analysis and PRD generation.

ARCHITECTURE NOTE:
Crew now accepts AgentContext for dependency injection, allowing tools
to access agent operations without tight coupling to pool manager.
"""

import json
import logging

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from app.agents.core.agent_context import AgentContext

from .tools import (
    load_prd_from_file, save_prd_to_file, update_prd_section,
    load_user_stories_from_file, save_user_stories_to_file, add_user_story,
    validate_prd_completeness, validate_user_story,
    create_ask_user_question_tool  # Factory for ask_user_question tool
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
        communication_style: str | None = None,
        tool_context: AgentContext | None = None
    ):
        self.agent_name = agent_name
        self.personality_traits = personality_traits or []
        self.communication_style = communication_style or "professional and clear"
        self.tool_context = tool_context
        
        # Create ask_user_question tool with injected context
        if tool_context:
            self.ask_user_question_tool = create_ask_user_question_tool(tool_context)
        else:
            # Fallback: Create dummy tool that returns error
            from crewai.tools import tool
            @tool
            def ask_user_question_dummy(*args, **kwargs):
                return {"error": "No tool context provided to crew"}
            self.ask_user_question_tool = ask_user_question_dummy
        
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
            tools=[load_prd_from_file, self.ask_user_question_tool],  # Can read PRD and ask user questions
            verbose=True
        )
    
    @agent
    def domain_expert(self) -> Agent:
        backstory = f"""{self.persona_description}

As a Domain Expert, you analyze business context and explain complex domain concepts clearly."""
        
        return Agent(
            config=self.agents_config['domain_expert'], # type: ignore[index]
            backstory=backstory,
            tools=[self.ask_user_question_tool],  # Can ask for domain/business clarification
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
                validate_prd_completeness,
                self.ask_user_question_tool  # Can ask for PRD specification details
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
    
    # workflow_orchestrator agent removed - using manager_llm instead
    # Custom manager_agent has issues with worker agent registration in CrewAI
    # Using manager_llm allows CrewAI to properly set up delegation tools
    
    @task
    def complete_ba_workflow_task(self) -> Task:
        """Main task for BA workflow - manager will delegate internally."""
        return Task(
            config=self.tasks_config['complete_ba_workflow'],  # type: ignore[index]
            # No agent specified - CrewAI assigns to auto-generated manager in hierarchical mode
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates hierarchical BA crew with auto-generated manager.
        
        Uses manager_llm instead of manager_agent to ensure worker agents
        are properly registered for delegation. CrewAI's automatic manager
        creation handles DelegateWorkTool setup correctly.
        
        In hierarchical mode with manager_llm:
        - CrewAI creates a default manager agent automatically
        - Worker agents are properly exposed as delegation targets
        - Manager can delegate using agent role names from agents.yaml
        - DelegateWorkTool and AskQuestionTool are set up correctly
        """
        from crewai import LLM
        
        # Worker agents - manager will be created automatically by CrewAI
        team_agents = [
            self.requirements_engineer(),
            self.domain_expert(),
            self.prd_specialist(),
            self.story_writer()
        ]
        
        return Crew(
            agents=team_agents,
            tasks=self.tasks, # type: ignore[index]
            process=Process.hierarchical,  # Hierarchical process
            manager_llm=LLM(model="gpt-4o", temperature=0.2),  # Let CrewAI create manager
            planning=True,  # Enable planning for better coordination
            verbose=True,
        )
