# app/agents/developer/test_agent.py
"""
Tests for the Developer Agent
"""

import pytest
import asyncio
from agent import create_developer_agent, run_developer_agent


@pytest.mark.asyncio
async def test_create_developer_agent():
    """Test creating the developer agent"""
    agent = create_developer_agent(
        working_directory=".",
        model_name="gpt-4o"
    )
    assert agent is not None
    print("✓ Developer agent created successfully")


@pytest.mark.asyncio
async def test_developer_agent_structure():
    """Test that developer agent has correct structure"""
    agent = create_developer_agent(
        working_directory=".",
        model_name="gpt-4o"
    )
    
    # Check that agent has required attributes
    assert hasattr(agent, 'invoke') or hasattr(agent, 'ainvoke')
    print("✓ Developer agent has correct structure")


def test_get_developer_instructions():
    """Test getting developer instructions"""
    from agent import get_developer_instructions
    
    instructions = get_developer_instructions(working_directory=".")
    assert instructions is not None
    assert "DEVELOPER AGENT" in instructions
    assert "Implementor" in instructions
    assert "Code Reviewer" in instructions
    print("✓ Developer instructions generated correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

