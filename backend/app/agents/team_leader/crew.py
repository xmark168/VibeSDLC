"""Team Leader Crew - Unified CrewAI workflow for Kanban-aware routing.

Following CrewAI best practices:
- ONE crew orchestrates entire workflow
- Sequential process with automatic context passing
- Agents specialized with detailed backstories
- Tasks with clear descriptions and expected outputs
"""

import logging
from typing import List

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent as CrewAIBaseAgent


logger = logging.getLogger(__name__)


@CrewBase
class TeamLeaderCrew:
    """Team Leader crew for Kanban-aware request routing.
    
    This crew follows CrewAI architecture:
    1. Analyze Kanban context (board state, WIP, metrics)
    2. Classify user intent (what they want)
    3. Make routing decision (where to send it)
    4. Generate natural response (communicate clearly)
    
    All tasks run sequentially with automatic context passing.
    """
    
    agents: List[CrewAIBaseAgent]
    tasks: List[Task]
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    # ===== AGENT DEFINITIONS =====
    
    @agent
    def kanban_context_analyzer(self) -> Agent:
        """Senior analyst who reads board telemetry and connects to user intent."""
        return Agent(
            config=self.agents_config['kanban_context_analyzer'],
            verbose=True
        )
    
    @agent
    def intent_classifier(self) -> Agent:
        """Conversational AI specialist who classifies user intent."""
        return Agent(
            config=self.agents_config['intent_classifier'],
            verbose=True
        )
    
    @agent
    def intelligent_router(self) -> Agent:
        """Routing specialist who makes Kanban-aware delegation decisions."""
        return Agent(
            config=self.agents_config['intelligent_router'],
            verbose=True
        )
    
    @agent
    def response_coordinator(self) -> Agent:
        """Communication specialist who crafts helpful responses."""
        return Agent(
            config=self.agents_config['response_coordinator'],
            verbose=True
        )
    
    # ===== TASK DEFINITIONS WITH CONTEXT CHAIN =====
    
    @task
    def analyze_kanban_context_task(self) -> Task:
        """Task 1: Analyze board state and user message."""
        return Task(
            config=self.tasks_config['analyze_kanban_context']
        )
    
    @task
    def classify_intent_task(self) -> Task:
        """Task 2: Classify user intent using context from Task 1."""
        return Task(
            config=self.tasks_config['classify_intent'],
            context=[self.analyze_kanban_context_task()]
        )
    
    @task
    def route_decision_task(self) -> Task:
        """Task 3: Make routing decision using context from Tasks 1 & 2."""
        return Task(
            config=self.tasks_config['route_decision'],
            context=[
                self.analyze_kanban_context_task(),
                self.classify_intent_task()
            ]
        )
    
    @task
    def generate_response_task(self) -> Task:
        """Task 4: Generate natural response using all previous context."""
        return Task(
            config=self.tasks_config['generate_response'],
            context=[
                self.analyze_kanban_context_task(),
                self.classify_intent_task(),
                self.route_decision_task()
            ]
        )
    
    # ===== THE ONE CREW =====
    
    @crew
    def crew(self) -> Crew:
        """Creates the unified Team Leader crew.
        
        This is the ONLY crew instance. It orchestrates the entire workflow:
        - All 4 agents work sequentially
        - All 4 tasks execute in order
        - Context flows automatically between tasks
        - One kickoff handles everything
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
