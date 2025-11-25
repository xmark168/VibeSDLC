"""Developer Crew - Multi-agent crew for project coordination."""

import logging
from pathlib import Path
from typing import Any
import os
import yaml
from crewai import LLM, Agent, Crew, Process, Task
from crewai_tools import TavilyExtractorTool, TavilySearchTool

from app.agents.developer.tools.custom_tool import (
    CodebaseSearchTool,
    ShellCommandTool,
)
from app.agents.developer.tools.filesystem_tools import (
    FileSearchTool,
    SafeFileDeleteTool,
    SafeFileEditTool,
    SafeFileListTool,
    SafeFileReadTool,
    SafeFileWriteTool,
)
from app.agents.developer.project_manager import project_manager

logger = logging.getLogger(__name__)


class DeveloperCrew:
    """Developer crew with multiple specialist agents.

    Crew composition:
    - Planner: Plans implementation based on requirements
    - Coder: Implement the plan from planner
    """

    def __init__(self, project_id: str = "default", root_dir: str = "../demo"):
        """Initialize Team Leader crew."""
        self.root_dir = root_dir
        self.project_id = project_id

        self.config = self._load_config()
        self.agents = self._create_agents()

    def _load_config(self) -> dict[str, Any]:
        """Load crew configuration from YAML.

        Returns:
            Configuration dictionary
        """
        config_path = Path(__file__).parent / "config.yaml"

        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _create_agents(self) -> dict[str, Agent]:
        """Create crew agents from configuration.

        Returns:
            Dictionary of agent name -> Agent instance
        """
        agents_config = self.config.get("agents", {})

        agents = {}

        # Planner
        planner_cfg = agents_config.get("planner", {})
        agents["planner"] = Agent(
            role=planner_cfg["role"],
            goal=planner_cfg["goal"],
            backstory=planner_cfg["backstory"],
            verbose=True,
            llm=LLM(
                model="openrouter/kwaipilot/kat-coder-pro:free",
                temperature=0.1,
                base_url="https://openrouter.ai/api/v1",
                api_key="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",
            ),
            tools=[
                # Semantic code search (RECOMMENDED - fastest way to find code using embeddings)
                CodebaseSearchTool(project_id=self.project_id),
                # Research tools
                TavilySearchTool(),
                TavilyExtractorTool(),
                # File reading - CRITICAL for reading AGENTS.md and package.json
                SafeFileReadTool(root_dir=self.root_dir),
                # Codebase analysis tools
                SafeFileListTool(root_dir=self.root_dir),
                FileSearchTool(root_dir=self.root_dir),
            ],
        )

        # Coder
        coder_cfg = agents_config.get("coder", {})
        agents["coder"] = Agent(
            role=coder_cfg["role"],
            goal=coder_cfg["goal"],
            backstory=coder_cfg["backstory"],
            verbose=True,
            allow_delegation=False,
            use_system_prompt=True,
            respect_context_window=True,
            llm=LLM(
                model="openrouter/kwaipilot/kat-coder-pro:free",
                temperature=0.1,
                base_url="https://openrouter.ai/api/v1",
                api_key="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",
            ),
            tools=[
                ShellCommandTool(root_dir=self.root_dir),
                CodebaseSearchTool(project_id=self.project_id),
                SafeFileWriteTool(root_dir=self.root_dir),
                SafeFileListTool(root_dir=self.root_dir),
                SafeFileReadTool(root_dir=self.root_dir),
                SafeFileEditTool(root_dir=self.root_dir),
                SafeFileDeleteTool(root_dir=self.root_dir),
            ],
        )

        logger.info(f"Created {len(agents)} agents for Team Leader crew")
        return agents

    async def implement_task(self, user_story: str) -> str:
        """Implement a development task.

        Uses the Planner and Coder to:
        1. Planning step_by_step so that coder can implement
        2. Implement the plan

        Args:
            task: Task to implement

        Returns:
            Working Code Result
        """
        # Register and index the project if it exists, or update if already registered
        if os.path.exists(self.root_dir):
            try:
                logger.info(f"Checking project registration for '{self.project_id}' at '{self.root_dir}'...")

                # Try to register the project if not already registered (this handles new projects)
                project_manager.register_project(self.project_id, self.root_dir)

                logger.info(f"Project index updated successfully for project '{self.project_id}'")
            except Exception as e:
                logger.error(f"Failed to register or update project index for project '{self.project_id}': {e}")
        else:
            logger.warning(f"Project directory does not exist: {self.root_dir}. Skipping indexing.")

        tasks_config = self.config.get("tasks", {})

        # Task 1: Plan the steps for coding agent
        plan_task_cfg = tasks_config.get("plan_task", {})
        plan_task = Task(
            description=plan_task_cfg["description"].format(
                user_story=user_story, working_dir=self.root_dir
            ),
            agent=self.agents["planner"],
            expected_output=plan_task_cfg["expected_output"],
        )

        # Task 2: Respond to user naturally
        code_task_cfg = tasks_config.get("code_task", {})
        code_task = Task(
            description=code_task_cfg["description"].format(
                user_story=user_story, working_dir=self.root_dir
            ),
            agent=self.agents["coder"],
            expected_output=code_task_cfg["expected_output"],
        )

        # Execute crew
        crew = Crew(
            agents=[
                self.agents["planner"],
                self.agents["coder"],
            ],
            tasks=[plan_task, code_task],
            process=Process.sequential,
            verbose=True,
            embedder={
                "provider": "openai",
                "config": {"model": "text-embedding-3-large"},
            },
            memory=True,
        )

        result = await crew.kickoff_async()

        # logic update 
        print(f"--- [After Kickoff] Crew run finished for project '{self.project_id}'. Updating index... ---")
        try:
            project_manager.update_project(self.project_id)
        except Exception as e:
            print(f"An unexpected error occurred during index update for project '{self.project_id}': {e}")
        
        return str(result)
