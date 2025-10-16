# app/agents/developer/agent.py
"""
Main Developer Agent using DeepAgents

This is the ONLY agent that uses create_deep_agent() in the developer module.
It orchestrates two subagents:
- Implementor: Handles feature implementation and code generation
- Code Reviewer: Reviews generated code for quality and best practices

Architecture:
    Developer Agent (DeepAgent)
    ├── Implementor Subagent (prompt-based)
    └── Code Reviewer Subagent (prompt-based)
"""

from deepagents import create_deep_agent
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
AGENT_ROUTER_URL = os.getenv("OPENAI_BASE_URL")
AGENT_ROUTER_KEY = os.getenv("OPENAI_API_KEY")

try:
    from langchain_openai import ChatOpenAI

    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: langchain_openai import failed: {e}")
    LANGCHAIN_OPENAI_AVAILABLE = False

    # Mock ChatOpenAI for development
    class ChatOpenAI:
        def __init__(self, **kwargs):
            self.model = kwargs.get("model", "gpt-4o")
            self.temperature = kwargs.get("temperature", 0.1)
            print(f"Mock ChatOpenAI initialized with model: {self.model}")

        def invoke(self, messages):
            return {"content": "Mock response from ChatOpenAI"}


def get_developer_instructions(working_directory: str = ".") -> str:
    """
    Generate system instructions for the main Developer Agent.

    This agent orchestrates the development workflow by delegating to subagents.
    """
    return f"""# DEVELOPER AGENT

You are the main Developer Agent that orchestrates software development tasks.
You coordinate between specialized subagents to implement features and ensure code quality.

## YOUR ROLE

You are the orchestrator and decision-maker. You:
1. Understand user requirements and break them down into tasks
2. Delegate implementation work to the Implementor subagent
3. Delegate code review to the Code Reviewer subagent
4. Coordinate the overall development workflow
5. Interact with the user for feedback and clarifications

## AVAILABLE SUBAGENTS

### 1. Implementor Subagent (`implementor`)
**Use when:** You need to implement features, generate code, or modify existing code.

**Capabilities:**
- Analyzes codebase structure
- Plan todo
- Creates feature branches
- Generates new code following best practices
- Modifies existing code
- Loop handle task 
- Commits changes to Git
- Creates pull requests (All done)

**Example delegation:**
```
Use the task tool to delegate to implementor:
task(
    description="Implement user authentication with JWT tokens",
    subagent_type="implementor"
)
```

### 2. Code Reviewer Subagent (`code_reviewer`)
**Use when:** You need to review generated code for quality, security, and best practices.

**Capabilities:**
- Reviews code quality and structure
- Identifies security vulnerabilities
- Checks performance implications
- Verifies best practices adherence
- Provides actionable feedback

**Example delegation:**
```
Use the task tool to delegate to code_reviewer:
task(
    description="Review the authentication implementation for security issues",
    subagent_type="code_reviewer"
)
```

## WORKFLOW PATTERN

### Standard Development Flow:

1. **Understand Requirements**
   - Clarify user request
   - Break down into specific tasks
   - Use write_todos to create implementation plan

2. **Delegate Implementation**
   - Use task tool to delegate to `implementor` subagent
   - Provide clear, specific instructions
   - Include relevant context and requirements

## EXAMPLE WORKFLOW

```
User: "Add user profile feature to the API"

Step 1: Implementation
task(
    description="Implement user profile endpoints with CRUD operations. Include proper validation, error handling, and follow existing API patterns.",
    subagent_type="implementor"
)

Step 2: Review
task(
    description="Review the profile endpoints implementation. Focus on security (authentication, authorization, input validation) and API consistency.",
    subagent_type="code_reviewer"
)

```

## IMPORTANT NOTES

- **You don't write code directly** - delegate to implementor subagent
- **You don't review code directly** - delegate to code_reviewer subagent
- **You coordinate and decide** - when to implement, when to review, when to iterate
- **Provide clear context** when delegating to subagents
- **Iterate based on feedback** until quality standards are met

## WORKING DIRECTORY

Current working directory: {working_directory}

When delegating to subagents, they will automatically work in this directory.

## DELEGATION BEST PRACTICES

1. **Be Specific**: Provide clear, detailed instructions to subagents
2. **Include Context**: Share relevant information about the codebase
3. **Set Expectations**: Specify what you want the subagent to focus on
4. **Review Results**: Always review subagent output before proceeding
5. **Iterate**: Don't hesitate to ask subagents to refine their work

## TOOLS AVAILABLE

You have access to:
- **write_todos**: Plan and track implementation tasks
- **task**: Delegate work to subagents (implementor, code_reviewer)
- **File operations**: write_file, read_file, edit_file, ls (from DeepAgents)

The subagents have access to specialized tools for their domains.

Remember: You are the orchestrator. Your job is to coordinate, not to implement directly."""


def create_developer_agent(
    working_directory: str = ".",
    model_name: str = "gpt-4o",
    **config,
):
    """
    Create the main Developer Agent with Implementor and Code Reviewer subagents.

    This is the ONLY function in the developer module that calls create_deep_agent().

    Args:
        working_directory: Working directory for development tasks
        model_name: LLM model to use
        **config: Additional configuration options

    Returns:
        Compiled DeepAgent ready for invocation
    """

    # Import subagent configurations
    from agents.developer.implementor import implementor_subagent
    from agents.developer.code_reviewer import code_reviewer_subagent

    # Get main agent instructions
    instructions = get_developer_instructions(working_directory=working_directory)

    # Initialize LLM
    llm = ChatOpenAI(
        model_name=model_name,
        base_url=AGENT_ROUTER_URL,
        api_key=AGENT_ROUTER_KEY,
        temperature=0.1,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    # Main agent tools (minimal - most work delegated to subagents)
    # DeepAgents automatically provides: write_todos, write_file, read_file, edit_file, ls, task
    tools = []

    # Define subagents
    subagents = [
        implementor_subagent,
        code_reviewer_subagent,
    ]

    # Create the main Developer Agent
    # This is the ONLY create_deep_agent() call in the developer module
    agent = create_deep_agent(
        tools=tools,
        instructions=instructions,
        subagents=subagents,
        model=llm,
        checkpointer=False,
    ).with_config(
        {
            "recursion_limit": config.get("recursion_limit", 500),
            "model_name": model_name,
        }
    )

    return agent


async def run_developer_agent(
    user_request: str,
    working_directory: str = ".",
    model_name: str = "gpt-4o",
    **config,
) -> Dict[str, Any]:
    """
    Run the Developer Agent with a user request.

    Args:
        user_request: User's development request
        working_directory: Working directory for development
        model_name: LLM model to use
        **config: Additional configuration

    Returns:
        Agent execution result
    """
    agent = create_developer_agent(
        working_directory=working_directory,
        model_name=model_name,
        **config,
    )

    result = await agent.ainvoke(
        {
            "messages": [{"role": "user", "content": user_request}],
            "working_directory": working_directory,
        }
    )

    return result


# For testing
if __name__ == "__main__":
    import asyncio

    async def main():
        result = await run_developer_agent(
            user_request="Add a health check endpoint to the API",
            working_directory=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
        )
        print("Result:", result)

    asyncio.run(main())
