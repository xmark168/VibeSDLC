"""
Tester Agent

QA Testing Specialist for ensuring software quality
"""

import yaml
from pathlib import Path
from typing import Any

from crewai import Agent
from crewai_tools import (
    FileReadTool,
    DirectoryReadTool,
    CodeDocsSearchTool,
)

from app.core.config import settings


def load_agent_config() -> dict[str, Any]:
    """Load agent configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "config" / "agents_config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def create_tester_agent() -> Agent:
    """
    Create and configure the Tester agent

    Returns:
        Configured CrewAI Agent instance
    """
    config = load_agent_config()
    tester_config = config["tester"]
    shared_config = config["shared"]

    # Initialize tools for tester
    # Note: Simplified tools that don't require API keys for testing
    tools = [
        FileReadTool(),          # Read test files and code
        DirectoryReadTool(),     # Analyze project structure
    ]

    # Create the agent
    agent = Agent(
        role=tester_config["role"],
        goal=tester_config["goal"],
        backstory=tester_config["backstory"],
        tools=tools,
        verbose=tester_config["verbose"],
        allow_delegation=tester_config["allow_delegation"],
        llm_config={
            "model": tester_config["model"],
            "temperature": settings.DEFAULT_LLM_TEMPERATURE,
            "max_tokens": settings.MAX_TOKENS,
        },
        max_iter=shared_config["max_iter"],
        max_rpm=shared_config["max_rpm"],
        memory=shared_config["memory"],
    )

    return agent


# Singleton instance
_tester_agent: Agent | None = None


def get_tester_agent() -> Agent:
    """Get or create Tester agent instance"""
    global _tester_agent

    if _tester_agent is None:
        _tester_agent = create_tester_agent()

    return _tester_agent
