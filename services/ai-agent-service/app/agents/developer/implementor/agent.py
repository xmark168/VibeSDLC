# app/agents/developer/implementor/agent.py
"""
Code Implementor Agent using DeepAgents

This agent implements features based on user requirements using the deepagents library.
It replaces the separate planner subagent by leveraging deepagents' built-in planning capabilities.

Key differences from separate planner approach:
- Uses deepagents' built-in write_todos for planning
- No manual graph construction - DeepAgents handles workflow
- Simpler state management with automatic persistence
- Built-in subagent support with isolated contexts
- Automatic human-in-the-loop support
"""

from deepagents import create_deep_agent
from typing import Dict, Any
import os
import sys

try:
    from langchain_openai import ChatOpenAI

    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: langchain_openai import failed: {e}")
    print("Using mock ChatOpenAI for development")
    LANGCHAIN_OPENAI_AVAILABLE = False

    # Mock ChatOpenAI class for development
    class ChatOpenAI:
        def __init__(self, **kwargs):
            self.model = kwargs.get("model", "gpt-4o")
            self.temperature = kwargs.get("temperature", 0.1)
            print(f"Mock ChatOpenAI initialized with model: {self.model}")

        def invoke(self, messages):
            return {"content": "Mock response from ChatOpenAI"}

        def stream(self, messages):
            yield {"content": "Mock streaming response from ChatOpenAI"}


from dotenv import load_dotenv

load_dotenv()
AGENT_ROUTER_URL = os.getenv("OPENAI_BASE_URL")
AGENT_ROUTER_KEY = os.getenv("OPENAI_API_KEY")

# Handle both package import and direct execution
if __name__ == "__main__":
    # Direct execution - add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from instructions import get_implementor_instructions
    from tools import (
        load_codebase_tool,
        index_codebase_tool,
        search_similar_code_tool,
        detect_stack_tool,
        retrieve_boilerplate_tool,
        create_feature_branch_tool,
        select_integration_strategy_tool,
        generate_code_tool,
        commit_changes_tool,
        create_pull_request_tool,
        collect_feedback_tool,
        refine_code_tool,
    )
    from subagents import code_generator_subagent, code_reviewer_subagent
else:
    # Package import - use relative imports
    from .instructions import get_implementor_instructions
    from .tools import (
        load_codebase_tool,
        index_codebase_tool,
        search_similar_code_tool,
        detect_stack_tool,
        retrieve_boilerplate_tool,
        create_feature_branch_tool,
        select_integration_strategy_tool,
        generate_code_tool,
        commit_changes_tool,
        create_pull_request_tool,
        collect_feedback_tool,
        refine_code_tool,
    )
    from .subagents import code_generator_subagent, code_reviewer_subagent


def create_implementor_agent(
    working_directory: str = ".",
    project_type: str = "existing",  # "new" or "existing"
    enable_pgvector: bool = True,
    boilerplate_templates_path: str = None,
    model_name: str = "gpt-4o",
    **config,
):
    """
    Create a DeepAgents-based implementor agent.

    Args:
        working_directory: Working directory for the agent
        project_type: "new" for new projects, "existing" for existing codebases
        enable_pgvector: Whether to enable pgvector indexing
        boilerplate_templates_path: Path to boilerplate templates
        model_name: LLM model to use
        **config: Additional configuration options

    Returns:
        Compiled DeepAgent ready for invocation
    """

    # Set default boilerplate path if not provided
    if boilerplate_templates_path is None:
        boilerplate_templates_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "templates", "boilerplate"
        )

    # Get implementor instructions
    instructions = get_implementor_instructions(
        working_directory=working_directory,
        project_type=project_type,
        enable_pgvector=enable_pgvector,
        boilerplate_templates_path=boilerplate_templates_path,
    )

    # Initialize LLM
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.1,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        base_url=AGENT_ROUTER_URL,
        api_key=AGENT_ROUTER_KEY,
    )

    # Define tools for implementation
    tools = [
        load_codebase_tool,
        index_codebase_tool,
        search_similar_code_tool,
        detect_stack_tool,
        retrieve_boilerplate_tool,
        create_feature_branch_tool,
        select_integration_strategy_tool,
        generate_code_tool,
        commit_changes_tool,
        create_pull_request_tool,
        collect_feedback_tool,
        refine_code_tool,
    ]

    # Define subagents for specialized tasks
    subagents = [
        code_generator_subagent,
        code_reviewer_subagent,
    ]

    # Create the deep agent
    # DeepAgents will automatically add:
    # - PlanningMiddleware with write_todos tool
    # - FilesystemMiddleware for mock file operations
    # - SubAgentMiddleware for spawning subagents
    # - SummarizationMiddleware for token management
    agent = create_deep_agent(
        tools=tools,
        instructions=instructions,
        subagents=subagents,
        model=llm,
    ).with_config(
        {
            "recursion_limit": config.get("recursion_limit", 500),
            "model_name": model_name,
        }
    )

    return agent


async def run_implementor(
    user_request: str,
    working_directory: str = ".",
    project_type: str = "existing",
    enable_pgvector: bool = True,
    boilerplate_templates_path: str = None,
    model_name: str = "gpt-4o",
    **config,
) -> Dict[str, Any]:
    """
    Run the implementor agent with a user request.

    This is the main entry point for using the implementor.

    Args:
        user_request: The user's implementation request
        working_directory: Working directory for the agent
        project_type: "new" for new projects, "existing" for existing codebases
        enable_pgvector: Whether to enable pgvector indexing
        boilerplate_templates_path: Path to boilerplate templates
        model_name: LLM model to use
        **config: Additional configuration

    Returns:
        Final state with implementation results

    Example:
        result = await run_implementor(
            user_request="Add user authentication with JWT",
            working_directory="./src",
            project_type="existing"
        )
        print(result['todos'])  # See implementation progress
    """

    # Create the agent
    agent = create_implementor_agent(
        working_directory=working_directory,
        project_type=project_type,
        enable_pgvector=enable_pgvector,
        boilerplate_templates_path=boilerplate_templates_path,
        model_name=model_name,
        **config,
    )

    # Create initial state
    initial_state = {
        "messages": [{"role": "user", "content": user_request}],
        "working_directory": working_directory,
        "project_type": project_type,
        "user_request": user_request,
        "enable_pgvector": enable_pgvector,
        "boilerplate_templates_path": boilerplate_templates_path,
        "implementation_status": "started",
        "generated_files": [],
        "commit_history": [],
    }

    # Run the agent
    # DeepAgents will automatically handle the workflow:
    # 1. Use write_todos to create implementation plan
    # 2. Execute each todo task
    # 3. Update todo status as tasks complete
    # 4. Handle user feedback and refinements
    result = await agent.ainvoke(initial_state)

    return result


# Example usage for testing
if __name__ == "__main__":
    import asyncio

    async def main():
        result = await run_implementor(
            user_request="Add user authentication with JWT tokens to the FastAPI application",
            working_directory="services/ai-agent-service/app/agents/demozzz",
            project_type="existing",
            enable_pgvector=True,
        )

        print("=" * 80)
        print("Implementation Results:")
        print("=" * 80)
        print(f"Status: {result.get('implementation_status', 'Unknown')}")
        print(f"Generated Files: {len(result.get('generated_files', []))}")
        print(f"Commits: {len(result.get('commit_history', []))}")

        if "todos" in result:
            print("\nTodos:")
            for i, todo in enumerate(result["todos"], 1):
                status = todo.get("status", "unknown")
                content = todo.get("content", "No content")
                print(f"{i}. [{status}] {content}")

    asyncio.run(main())
