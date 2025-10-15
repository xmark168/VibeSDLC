# app/agents/developer/planner/agent.py
"""
Planner Agent using DeepAgents

This is a reimplementation of the planner using DeepAgents instead of LangGraph.
DeepAgents provides a simpler, higher-level abstraction for building agents.

Key differences from LangGraph version:
- No manual graph construction - DeepAgents handles workflow
- Simpler state management
- Built-in subagent support
- Auto-handles planning and execution
"""

from deepagents import create_deep_agent
from typing import List, Optional, Dict, Any
import os
import sys
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
AGENT_ROUTER_URL = os.getenv("OPENAI_BASE_URL")
AGENT_ROUTER_KEY = os.getenv("OPENAI_API_KEY")
# Handle both package import and direct execution
if __name__ == "__main__":
    # Direct execution - add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from instructions import get_planner_instructions
    from tools import (
        grep_search_tool,
        view_file_tool,
        shell_execute_tool,
        list_directory_tool,
        take_notes_tool,
        code_search_tool,
        ast_parser_tool,
        dependency_analyzer_tool,
    )
    from subagents import plan_generator_subagent, note_taker_subagent
    from state import PlannerAgentState
else:
    # Package import - use relative imports
    from .instructions import get_planner_instructions
    from .tools import (
        grep_search_tool,
        view_file_tool,
        shell_execute_tool,
        list_directory_tool,
        take_notes_tool,
        code_search_tool,
        ast_parser_tool,
        dependency_analyzer_tool,
    )
    from .subagents import plan_generator_subagent, note_taker_subagent
    from .state import PlannerAgentState


def create_planner_agent(
    working_directory: str = ".",
    custom_rules: Optional[Dict[str, Any]] = None,
    codebase_tree: str = "",
    model_name: str = "deepseek-chat",  # DeepSeek-V3 (supports tool calling)
    **config
):
    """
    Create a DeepAgents-based planner agent.

    Args:
        working_directory: Working directory for the agent
        custom_rules: Optional custom rules for the codebase
        codebase_tree: Optional pre-generated codebase tree
        model_name: LLM model to use
        **config: Additional configuration options

    Returns:
        Compiled DeepAgent ready for invocation
    """

    # Get planner instructions
    instructions = get_planner_instructions(
        working_directory=working_directory,
        custom_rules=custom_rules,
        codebase_tree=codebase_tree
    )

    # Use ChatDeepSeek for DeepSeek models (supports tool calling)
    # Note: DeepSeek-R1 does NOT support tool calling, so we use DeepSeek-V3
    llm = ChatOpenAI(
        model="gpt-4o",  # DeepSeek-V3 with tool calling support
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        base_url=AGENT_ROUTER_URL,
        api_key=AGENT_ROUTER_KEY,
    )
    # Define tools for context gathering
    tools = [
        grep_search_tool,
        view_file_tool,
        shell_execute_tool,
        list_directory_tool,
        take_notes_tool,
        code_search_tool,
        ast_parser_tool,
        dependency_analyzer_tool,
    ]

    subagents = [
        plan_generator_subagent,
        note_taker_subagent,
    ]

    # Create the deep agent
    agent = create_deep_agent(
        tools=tools,
        instructions=instructions,
        subagents=subagents,
        model=llm,
    ).with_config({
        "recursion_limit": config.get("recursion_limit", 500),
        "model_name": "gpt-4o",  # DeepSeek-V3
    })

    return agent


async def run_planner(
    user_request: str,
    working_directory: str = ".",
    custom_rules: Optional[Dict[str, Any]] = None,
    codebase_tree: str = "",
    model_name: str = "gpt-4",
    **config
) -> Dict[str, Any]:
    """
    Run the planner agent with a user request.

    This is the main entry point for using the planner.

    Args:
        user_request: The user's request/task description
        working_directory: Working directory for the agent
        custom_rules: Optional custom rules
        codebase_tree: Optional codebase structure
        model_name: LLM model to use
        **config: Additional configuration

    Returns:
        Final state with proposed plan and context notes

    Example:
        result = await run_planner(
            user_request="Add user authentication with JWT",
            working_directory="./src",
            custom_rules={"general_rules": "Follow PEP 8"}
        )
        print(result['proposed_plan'])
    """

    # Create the agent
    agent = create_planner_agent(
        working_directory=working_directory,
        custom_rules=custom_rules,
        codebase_tree=codebase_tree,
        model_name=model_name,
        **config
    )

    # Create initial state
    initial_state = {
        "messages": [{"role": "user", "content": user_request}],
        "working_directory": working_directory,
        "codebase_tree": codebase_tree,
        "custom_rules": custom_rules,
        "user_request": user_request,
        "proposed_plan": [],
        "context_gathering_notes": "",
        "scratchpad_notes": [],
    }

    # Invoke the agent
    # DeepAgents handles the entire workflow:
    # 1. Context gathering with tools
    # 2. Plan generation via subagent
    # 3. Note taking via subagent
    result = await agent.ainvoke(initial_state, config)

    return result


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        result = await run_planner(
            user_request="Add user authentication with JWT tokens to the FastAPI application",
            working_directory="ai-agent-service/app/agents/demo",
            codebase_tree="""
                src/
                  api/
                    routes/
                    models/
                  auth/
                  services/
                  utils/
            """
            ,
            # custom_rules={
            #     "general_rules": "Follow PEP 8 style guide. Use type hints.",
            #     "testing_instructions": "Write pytest tests with 80%+ coverage"
            # }
        )

        print("=" * 80)
        print(f"Plan Title: {result.get('proposed_plan_title', 'Implementation Plan')}")
        print("=" * 80)
        print("\nProposed Plan:")
        for i, step in enumerate(result.get('proposed_plan', []), 1):
            print(f"{i}. {step}")

        print("\n" + "=" * 80)
        print("Context Notes:")
        print("=" * 80)
        print(result.get('context_gathering_notes', 'No notes'))

    asyncio.run(main())
