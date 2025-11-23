from crewai import Agent, Crew, Knowledge, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
import subprocess
import os
from crewai.knowledge.source.crew_docling_source import CrewDoclingSource
from crewai.project import CrewBase, agent, crew, task, after_kickoff
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai_tools import TavilySearchTool,TavilyExtractorTool
from crewai import LLM
import glob
from .tools.custom_tool import (
    CodebaseSearchTool,
    DuckDuckGoSearchTool,
    ShellCommandTool,
)
from .tools.filesystem_tools import (
    FileSearchTool,
    SafeFileDeleteTool,
    SafeFileEditTool,
    SafeFileListTool,
    SafeFileReadTool,
    SafeFileWriteTool,
)
from .project_manager import project_manager

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

# Create Next.js knowledge source

from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.crew_docling_source import CrewDoclingSource


# Create a knowledge source from web content



@CrewBase
class Dev:
    """Dev crew"""

    agents: list[BaseAgent]
    tasks: list[Task]
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    root_dir: str = None  # Store root_dir as instance variable
    files = glob.glob("knowledge/**/*.mdx", recursive=True)
    files = [os.path.relpath(file, "knowledge") for file in files]
    crew_docs = TextFileKnowledgeSource(file_paths=files)
    content_docs = CrewDoclingSource(
    file_paths=[
        "https://nextjs.org/docs/app/getting-started/project-structure",
        "https://nextjs.org/docs/app/getting-started/layouts-and-pages",
        "https://nextjs.org/docs/app/getting-started/linking-and-navigating",
        "https://nextjs.org/docs/app/getting-started/server-and-client-components",
        "https://nextjs.org/docs/app/getting-started/cache-components",
        "https://nextjs.org/docs/app/getting-started/fetching-data",
        "https://nextjs.org/docs/app/getting-started/updating-data",
        "https://nextjs.org/docs/app/getting-started/caching-and-revalidating",
        "https://nextjs.org/docs/app/getting-started/error-handling",
        "https://nextjs.org/docs/app/getting-started/css",
        "https://nextjs.org/docs/app/getting-started/images",
        "https://nextjs.org/docs/app/getting-started/fonts",
        "https://nextjs.org/docs/app/getting-started/metadata-and-og-images",
        "https://nextjs.org/docs/app/getting-started/route-handlers",
        "https://nextjs.org/docs/app/getting-started/proxy",
        "https://nextjs.org/docs/app/getting-started/deploying",
        "https://nextjs.org/docs/app/getting-started/upgrading",
        "https://nextjs.org/docs/app/getting-started/fonts",
    ],
)
    def __init__(self, project_id: str = "demo", root_dir: str = None):
        """Initialize Dev crew with a project_id and optional root_dir."""
        self.project_id = project_id
        if root_dir:
            self.root_dir = root_dir
        else:
            # Default to a workspace path if no root_dir is provided
            self.root_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "demo",
                project_id,
            )
        # Ensure the project is registered with the manager
        # Check if the project path exists before registering
        # LOGIC VALIDATE IF WORKSPACE IS INDEXED
        if os.path.exists(self.root_dir):
            project_manager.register_project(self.project_id, self.root_dir)
        else:
            print(f"Warning: Project directory not found, skipping registration for {self.project_id}")


    @after_kickoff
    def update_index_after_run(self, result):
        """This method is executed after the crew kickoff is finished, regardless of success."""
        print(f"--- [After Kickoff] Crew run finished for project '{self.project_id}'. Updating index... ---")
        try:
            project_manager.update_project(self.project_id)
        except Exception as e:
            print(f"An unexpected error occurred during index update for project '{self.project_id}': {e}")

    @agent
    def planning_agent(self) -> Agent:
        """Create a planning agent with research capabilities"""
        return Agent(
            config=self.agents_config["planning_agent"],
            verbose=True,
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
            llm=LLM(
                model="openrouter/kwaipilot/kat-coder-pro:free",
                  temperature=0.1,base_url="https://openrouter.ai/api/v1", 
                  api_key="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"
                  )
        )

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def coding_agent(self) -> Agent:
        """Create a coding agent with file management and search capabilities"""
        
        return Agent(
            config=self.agents_config["coding_agent"],
            allow_code_execution=False,
            max_retry_limit=3,
            max_iter=50,  # Allow agent to perform up to 25 actions/thoughts
            verbose=True,
            tools=[
                ShellCommandTool(root_dir=self.root_dir),
                # Semantic code search
                CodebaseSearchTool(project_id=self.project_id),
                # File reading and writing
                SafeFileWriteTool(root_dir=self.root_dir),
                SafeFileListTool(
                    root_dir=self.root_dir
                ),  # Added for file path verification
                # Legacy tools
                SafeFileReadTool(root_dir=self.root_dir),
                SafeFileEditTool(root_dir=self.root_dir),
                SafeFileDeleteTool(root_dir=self.root_dir),
            ],
                      llm=LLM(
                    model="openrouter/kwaipilot/kat-coder-pro:free",
                  temperature=0.1,base_url="https://openrouter.ai/api/v1", 
                  api_key="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"
                  ),
                #   knowledge_sources=[self.crew_docs,content_source],

        )

    @agent
    def code_reviewer(self) -> Agent:
        """Create a code review agent (optional)"""
        return Agent(config=self.agents_config["code_reviewer"], verbose=True)

    @task
    def planning_task(self) -> Task:
        """Define the planning task"""
        return Task(
            config=self.tasks_config["planning_task"], agent=self.planning_agent()
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def coding_task(self) -> Task:
        """Define the main coding task"""
        return Task(
            config=self.tasks_config["coding_task"],
            agent=self.coding_agent(),
            # context=[self.planning_task()]
        )

    @task
    def review_task(self) -> Task:
        """Define the code review task (optional)"""
        return Task(config=self.tasks_config["review_task"], agent=self.code_reviewer())

    @crew
    def crew(self) -> Crew:
        """Creates the MyProject crew"""
        return Crew(
            agents=[self.planning_agent(), self.coding_agent()],
            tasks=[self.planning_task(), self.coding_task()],
            process=Process.sequential,
            verbose=True,
            memory=True,
            knowledge_sources=[self.content_docs],
            # embedder={
            #     "provider": "voyageai",
            #     "config": {
            #         "model": "voyage-3-large",
            #         "api_key": "pa-_RrNKfNCL9jRxP1Fxx4DvfinH53XbI1QzSVrxTckORP",
            #     }
            # },
                embedder={  
                    "provider": "openai",
                    "config": {"model": "text-embedding-3-large"}
                }
        )