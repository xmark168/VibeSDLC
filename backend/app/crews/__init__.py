"""
CrewAI-based Multi-Agent System

This package implements a multi-agent system using CrewAI framework with:
- Event-driven architecture (Kafka)
- Pull system for task distribution
- Flow-based orchestration
- 4 specialized agents: Team Leader, Business Analyst, Developer, Tester
"""

from app.crews.agents import (
    get_business_analyst_agent,
    get_developer_agent,
    get_tester_agent,
    get_team_leader_agent,
)
from app.crews.flows import (
    DevelopmentFlow,
    DevelopmentFlowState,
    create_development_flow,
)
from app.crews.events import (
    kafka_producer,
    kafka_consumer,
    event_schemas,
)

__all__ = [
    # Agents
    "get_business_analyst_agent",
    "get_developer_agent",
    "get_tester_agent",
    "get_team_leader_agent",
    # Flows
    "DevelopmentFlow",
    "DevelopmentFlowState",
    "create_development_flow",
    # Events
    "kafka_producer",
    "kafka_consumer",
    "event_schemas",
]
