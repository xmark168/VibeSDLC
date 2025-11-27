"""Developer Crew - Multi-agent crew for project coordination."""

import logging
from pathlib import Path
from typing import Any
import os
import glob
import yaml
from datetime import datetime
from crewai import LLM, Agent, Crew, Process, Task
from crewai_tools import TavilyExtractorTool, TavilySearchTool
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
        
from app.agents.developer.tools.custom_tool import (
    CodebaseSearchTool,
    ShellCommandTool,
)
from app.agents.developer.tools.git_python_tool import GitPythonTool
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
                    model="openai/alibaba-qwen3-32b",
                  temperature=0.1,base_url="https://ai.megallm.io/v1", 
                  api_key="sk-mega-f2cad3ab748b80af3cc310789c808c7c83efc342729e533067d60d4b8db4cd01"
            ),
            tools=[
                CodebaseSearchTool(project_id=self.project_id),
                TavilySearchTool(),
                TavilyExtractorTool(),
                SafeFileReadTool(root_dir=self.root_dir),
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
                    model="openai/alibaba-qwen3-32b",
                  temperature=0.1,base_url="https://ai.megallm.io/v1", 
                  api_key="sk-mega-f2cad3ab748b80af3cc310789c808c7c83efc342729e533067d60d4b8db4cd01"
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

    async def implement_task(self, user_story: str, task_id: str = None) -> str:
        """Implement a development task.

        Uses the Planner and Coder to:
        1. Planning step_by_step so that coder can implement
        2. Implement the plan

        Args:
            user_story: Description of the task to implement
            task_id: Unique identifier for this task (if not provided, will be generated)

        Returns:
            Working Code Result
        """
        # Index the main workspace first
        if os.path.exists(self.root_dir):
            try:
                logger.info(f"Checking project registration for '{self.project_id}' at '{self.root_dir}'...")
                project_manager.register_project(self.project_id, self.root_dir)
                logger.info(f"Project index updated successfully for project '{self.project_id}'")
            except Exception as e:
                logger.error(f"Failed to register or update project index for project '{self.project_id}': {e}")
        else:
            logger.warning(f"Project directory does not exist: {self.root_dir}. Skipping indexing.")

        # Generate task ID if not provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if task_id is None:
            task_id = f"ai-task-{timestamp}-{hash(user_story) % 10000:04d}"

        short_task_id = task_id.split('-')[-1] if '-' in task_id else task_id[:8]
        branch_name = f"story_{short_task_id}"

        # Initialize Git in main workspace if needed
        git_tool = GitPythonTool(root_dir=self.root_dir)
        init_result = git_tool._run("init", message="Initializing project git repo")
        print(f" Git init result: {init_result}")

        # Make initial commit in main workspace if needed
        status_result = git_tool._run("status")
        if "nothing to commit" not in status_result and "No commits yet" in status_result:
            print(" Creating initial commit in main workspace...")
            git_tool._run("commit", message="Initial commit", files=["."])

        # Create Git worktree for this task
        print(f" Creating Git worktree for branch '{branch_name}'...")
        worktree_result = git_tool._run("create_worktree", branch_name=branch_name)
        print(f"Git worktree result: {worktree_result}")

        # Determine worktree path
        worktree_path = Path(self.root_dir).parent / f"ws_story_{short_task_id}"

        # Check if worktree was created successfully
        if worktree_path.exists() and worktree_path.is_dir():
            print(f"✓ Worktree created successfully: {worktree_path}")

            # Switch to worktree for all operations
            active_root_dir = str(worktree_path)
            active_git_tool = GitPythonTool(root_dir=active_root_dir)

            # Update all agent tools to use worktree path
            for agent_name, agent in self.agents.items():
                for tool in agent.tools:
                    if hasattr(tool, 'root_dir'):
                        tool.root_dir = active_root_dir
                        print(f"  → Updated {tool.name} root_dir to: {active_root_dir}")

            # Register task workspace for indexing
            try:
                logger.info(f"Registering task workspace for indexing: '{task_id}' in project '{self.project_id}'")
                project_manager.register_task(self.project_id, task_id, active_root_dir)
            except Exception as e:
                logger.error(f"Failed to register task workspace for indexing: {e}")

        else:
            # Fallback to main workspace if worktree creation failed
            print(f" Worktree not created, falling back to main workspace: {self.root_dir}")
            print(f"  Creating branch '{branch_name}' in main workspace instead...")

            active_root_dir = self.root_dir
            active_git_tool = git_tool

            # Create branch and checkout
            git_tool._run("create_branch", branch_name=branch_name)

        # Now create the tasks with the active workspace
        tasks_config = self.config.get("tasks", {})

        plan_task_cfg = tasks_config.get("plan_task", {})
        plan_task = Task(
            description=plan_task_cfg["description"].format(
                user_story=user_story, working_dir=active_root_dir
            ),
            agent=self.agents["planner"],
            expected_output=plan_task_cfg["expected_output"],
        )

        code_task_cfg = tasks_config.get("code_task", {})
        code_task = Task(
            description=code_task_cfg["description"].format(
                user_story=user_story, working_dir=active_root_dir
            ),
            agent=self.agents["coder"],
            expected_output=code_task_cfg["expected_output"],
        )

        # Load knowledge sources
        developer_dir = Path(__file__).parent
        knowledge_dir = developer_dir / "knowledge"

        # Save current working directory and change to developer_dir
        # because TextFileKnowledgeSource expects relative paths from cwd
        original_cwd = os.getcwd()

        knowledge_files = []
        if knowledge_dir.exists():
            # Change to developer_dir so relative paths work correctly
            os.chdir(developer_dir)

            for ext in ["**/*.md", "**/*.txt", "**/*.mdx"]:
                for file_path in knowledge_dir.glob(ext):
                    if file_path.exists() and file_path.is_file():
                        # Use relative path from developer_dir (which is now cwd)
                        relative_path = file_path.relative_to(developer_dir)
                        knowledge_files.append(str(relative_path))

        knowledge_sources = []
        if knowledge_files:
            try:
                if knowledge_files:
                    text_knowledge = TextFileKnowledgeSource(file_paths=knowledge_files)
                    knowledge_sources = [text_knowledge]
                    logger.info(f"Loaded {len(knowledge_files)} knowledge files from {knowledge_dir}")
                    logger.info(f"Knowledge files (relative): {knowledge_files}")
                else:
                    logger.info("No existing knowledge files found to load")
            except Exception as e:
                logger.error(f"Error loading knowledge sources: {e}")
                logger.error(f"Attempted to load these files: {knowledge_files}")
                logger.error(f"Knowledge directory: {knowledge_dir}, exists: {knowledge_dir.exists()}")
            finally:
                # Restore original working directory
                os.chdir(original_cwd)

        # Execute crew
        crew = Crew(
            agents=[
                self.agents["planner"],
                self.agents["coder"],
            ],
            tasks=[plan_task, code_task],
            process=Process.sequential,
            verbose=True,
            # knowledge_sources=knowledge_sources,  # Add knowledge sources
            # embedder={
            #     "provider": "openai",
            #     "config": {"model": "text-embedding-3-large"},
            # },
            # memory=True,
        )

        result = await crew.kickoff_async()


        commit_result = active_git_tool._run("commit", message=f"Auto-commit: Implementing task - {user_story[:50]}...", files=["."])
        print(f" Git commit result: {commit_result}")

        # Check if we're in worktree
        if worktree_path.exists() and str(worktree_path) == active_root_dir:
            print(f" Changes committed in worktree: {worktree_path}")
            print(f"  Branch: {branch_name}")
            print(f"  To merge back to main:")
            print(f"    cd {self.root_dir}")
            print(f"    git merge {branch_name}")
        else:
            print(f" Changes committed in main workspace: {active_root_dir}")

        # Update both project and task indexes
        print(f"--- [After Kickoff] Crew run finished for project '{self.project_id}'. Updating indexes... ---")
        try:
            # Update the main project index
            await project_manager.update_project(self.project_id)

            # Update the task-specific index
            # Use the task_id that was passed in or generated
            await project_manager.update_task(self.project_id, task_id)
            print(f"Task index updated for task '{task_id}' in project '{self.project_id}'")

        except Exception as e:
            print(f"An unexpected error occurred during index update: {e}")

        return str(result)

    async def report_progress(self, query: str, project_id: str = "default", task_id: str = None) -> str:
        """Report on project or specific task progress based on the query.

        Args:
            query: User's query about progress (e.g., "What's the status?", "How far along are we?")
            project_id: Project identifier for context
            task_id: Specific task ID if querying about specific task (optional)

        Returns:
            Progress report based on available information and query
        """
        # Get the appropriate agent for progress reporting
        reporter_agent = self.agents["coder"]  # Use the Coder agent that has knowledge of the codebase

        progress_description = f"""
Analyze and report on the development progress based on the following query:

Query: {query}
Project ID: {project_id}
Task ID: {task_id or 'Not specified'}

Based on the current codebase and your knowledge, provide a helpful progress report that includes:

If it's a general progress query:
- Features implemented so far
- Current development status
- What's working
- What's planned next
- Any development bottlenecks or considerations

If it's about a specific task:
- Status of that specific task
- What code has been affected
- Dependencies or related components
- Estimated completion if possible

Be concise but informative, friendly and professional.
"""

        progress_task = Task(
            description=progress_description,
            expected_output="Concise and informative progress report that addresses the user's query",
            agent=reporter_agent,
        )

        # Execute crew
        crew = Crew(
            agents=[reporter_agent],
            tasks=[progress_task],
            process=Process.sequential,
            verbose=True,
            # knowledge_sources=[],  # Use current knowledge as needed
            # embedder={
            #     "provider": "openai",
            #     "config": {"model": "text-embedding-3-large"},
            # },
            # memory=True,
        )

        result = await crew.kickoff_async()

        return str(result)

    async def react_task(self, story_details: str, user_request: str, project_id: str = "default", task_id: str = None) -> str:
        """Handle user's additional feature/interface requests for a specific story/task.

        Args:
            story_details: Details about the existing story/task that user wants to extend
            user_request: User's specific request for additional features/interfaces
            project_id: Project identifier for context
            task_id: Specific task ID if applicable (optional)

        Returns:
            Response with implementation plan or feasibility analysis for the requested additions
        """
        # Use the Coder agent to handle the user's additional requests
        coder_agent = self.agents["coder"]

        react_description = f"""
Analyze and respond to the user's request for additional features/interfaces on an existing story/task:

Existing Story/Task Details: {story_details}
User's Additional Request: {user_request}
Project ID: {project_id}
Task ID: {task_id or 'Not specified'}

Based on the current codebase, requirements, and your knowledge:

1. Analyze Feasibility:
- Is the requested feature/interface technically feasible?
- What existing components can be reused?
- What new components need to be created?

2. Implementation Approach:
- How should this be integrated with existing functionality?
- What files/components need to be modified?
- What new files/components need to be created?
- Consider UI/UX implications if it's interface-related
- Consider API/database changes if it affects data flow

3. Dependencies & Impact:
- Does this affect other parts of the system?
- Are there any breaking changes?
- What testing would be needed?

4. Provide clear, actionable next steps

Be constructive, professional, and specific in your response.
"""

        react_task = Task(
            description=react_description,
            expected_output="Detailed response analyzing the feasibility of the user's request with implementation approach and next steps",
            agent=coder_agent,
        )

        # Execute crew
        crew = Crew(
            agents=[coder_agent],
            tasks=[react_task],
            process=Process.sequential,
            verbose=True,
            # knowledge_sources=[],  # Use current knowledge as needed
            # embedder={
            #     "provider": "openai",
            #     "config": {"model": "text-embedding-3-large"},
            # },
            # memory=True,
        )

        result = await crew.kickoff_async()

        return str(result)
