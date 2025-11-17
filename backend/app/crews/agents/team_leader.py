"""
Team Leader Agent

Technical Team Leader and Flow Manager for orchestrating development workflow
"""

import yaml
from pathlib import Path
from typing import Any

from crewai import Agent
from crewai_tools import (
    FileReadTool,
    DirectoryReadTool,
    SerperDevTool,
)

from app.core.config import settings


def load_agent_config() -> dict[str, Any]:
    """Load agent configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "config" / "agents_config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def create_team_leader_agent() -> Agent:
    """
    Create and configure the Team Leader agent

    Returns:
        Configured CrewAI Agent instance
    """
    config = load_agent_config()
    tl_config = config["team_leader"]
    shared_config = config["shared"]

    # Initialize tools for team leader
    # Note: Simplified tools that don't require API keys for testing
    tools = [
        FileReadTool(),          # Read project files
        DirectoryReadTool(),     # Analyze project structure
    ]

    # Create the agent
    agent = Agent(
        role=tl_config["role"],
        goal=tl_config["goal"],
        backstory=tl_config["backstory"],
        tools=tools,
        verbose=tl_config["verbose"],
        allow_delegation=tl_config["allow_delegation"],  # True - can delegate to other agents
        llm_config={
            "model": tl_config["model"],
            "temperature": settings.DEFAULT_LLM_TEMPERATURE,
            "max_tokens": settings.MAX_TOKENS,
        },
        max_iter=shared_config["max_iter"],
        max_rpm=shared_config["max_rpm"],
        memory=shared_config["memory"],
    )

    return agent


# Singleton instance
_team_leader_agent: Agent | None = None


def get_team_leader_agent() -> Agent:
    """Get or create Team Leader agent instance"""
    global _team_leader_agent

    if _team_leader_agent is None:
        _team_leader_agent = create_team_leader_agent()

    return _team_leader_agent
