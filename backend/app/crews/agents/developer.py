"""
Developer Agent

Senior Full-Stack Developer for implementing features and writing code
"""

import yaml
from pathlib import Path
from typing import Any

from crewai import Agent
from crewai_tools import (
    FileReadTool,
    DirectoryReadTool,
    CodeDocsSearchTool,
    GithubSearchTool,
)

from app.core.config import settings


def load_agent_config() -> dict[str, Any]:
    """Load agent configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "config" / "agents_config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def create_developer_agent() -> Agent:
    """
    Create and configure the Developer agent

    Returns:
        Configured CrewAI Agent instance
    """
    config = load_agent_config()
    dev_config = config["developer"]
    shared_config = config["shared"]

    # Initialize tools for developer
    # Note: Simplified tools that don't require API keys for testing
    tools = [
        FileReadTool(),          # Read code files
        DirectoryReadTool(),     # Analyze project structure
    ]

    # Create the agent
    agent = Agent(
        role=dev_config["role"],
        goal=dev_config["goal"],
        backstory=dev_config["backstory"],
        tools=tools,
        verbose=dev_config["verbose"],
        allow_delegation=dev_config["allow_delegation"],
        llm_config={
            "model": dev_config["model"],
            "temperature": settings.DEFAULT_LLM_TEMPERATURE,
            "max_tokens": settings.MAX_TOKENS,
        },
        max_iter=shared_config["max_iter"],
        max_rpm=shared_config["max_rpm"],
        memory=shared_config["memory"],
    )

    return agent


# Singleton instance
_developer_agent: Agent | None = None


def get_developer_agent() -> Agent:
    """Get or create Developer agent instance"""
    global _developer_agent

    if _developer_agent is None:
        _developer_agent = create_developer_agent()

    return _developer_agent
