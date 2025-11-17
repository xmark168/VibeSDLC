"""
Business Analyst Agent

Transforms business requirements into clear, actionable technical specifications
"""

import yaml
from pathlib import Path
from typing import Any

from crewai import Agent
from crewai_tools import (
    SerperDevTool,
    FileReadTool,
    DirectoryReadTool,
)

from app.core.config import settings


def load_agent_config() -> dict[str, Any]:
    """Load agent configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "config" / "agents_config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def create_business_analyst_agent() -> Agent:
    """
    Create and configure the Business Analyst agent

    Returns:
        Configured CrewAI Agent instance
    """
    config = load_agent_config()
    ba_config = config["business_analyst"]
    shared_config = config["shared"]

    # Initialize tools for business analyst
    # Note: Simplified tools that don't require API keys for testing
    tools = [
        FileReadTool(),   # Read project files
        DirectoryReadTool(),  # Analyze project structure
    ]

    # Create the agent
    agent = Agent(
        role=ba_config["role"],
        goal=ba_config["goal"],
        backstory=ba_config["backstory"],
        tools=tools,
        verbose=ba_config["verbose"],
        allow_delegation=ba_config["allow_delegation"],
        llm_config={
            "model": ba_config["model"],
            "temperature": settings.DEFAULT_LLM_TEMPERATURE,
            "max_tokens": settings.MAX_TOKENS,
        },
        max_iter=shared_config["max_iter"],
        max_rpm=shared_config["max_rpm"],
        memory=shared_config["memory"],
    )

    return agent


# Singleton instance
_business_analyst_agent: Agent | None = None


def get_business_analyst_agent() -> Agent:
    """Get or create Business Analyst agent instance"""
    global _business_analyst_agent

    if _business_analyst_agent is None:
        _business_analyst_agent = create_business_analyst_agent()

    return _business_analyst_agent
