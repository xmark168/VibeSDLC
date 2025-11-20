"""Team Leader task definitions.

Tasks for analyzing user messages and delegating to specialists.
"""

from typing import Any, Dict

from crewai import Agent, Task


def create_analyze_and_delegate_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for analyzing user message and delegating to specialist.

    Args:
        agent: Team Leader agent
        context: Context containing user_message

    Returns:
        CrewAI Task for analysis and delegation
    """
    user_message = context.get("user_message", "")

    task_description = f"""
    Analyze the following user message and determine how to handle it:

    User Message: {user_message}

    You have two options:

    **OPTION 1: Handle directly (for simple queries)**
    Use this when the message is:
    - Greetings (hi, hello, xin chào, etc.)
    - Start commands (bắt đầu, start, begin) - respond by greeting and asking what they want to build
    - General questions about the project or team
    - Small talk or casual conversation
    - Questions you can answer without specialist knowledge
    - Acknowledgments (ok, thanks, understood, etc.)

    IMPORTANT: When user says "Bắt đầu" or "start", greet them warmly and ask what software/application they want to build.

    **OPTION 2: Delegate to specialist (for domain-specific tasks)**
    Available specialists:
    - business_analyst: For requirements gathering, PRD creation, user stories, product analysis, feature discussions
    - developer: For code implementation, technical solutions, architecture design, bug fixes
    - tester: For QA planning, test cases, validation, quality assurance, testing strategies

    Keywords for specialists:
    - Business Analyst: "requirements", "user story", "PRD", "acceptance criteria", "features", "needs", "analyze", "build software", "create app"
    - Developer: "implement", "code", "build", "create", "develop", "fix bug", "architecture", "programming"
    - Tester: "test", "QA", "validate", "quality", "coverage", "test plan", "test cases"

    Respond ONLY with a valid JSON object (no markdown, no code blocks):

    For direct response:
    {{
        "specialist": "none",
        "direct_response": "Your friendly response to the user",
        "reasoning": "Why you're handling this directly"
    }}

    For delegation:
    {{
        "specialist": "business_analyst" | "developer" | "tester",
        "task_description": "Clear description of what the specialist should do",
        "priority": "high" | "medium" | "low",
        "context": "Any relevant context or constraints",
        "reasoning": "Brief explanation of why this specialist was chosen"
    }}
    """

    expected_output = """
    A valid JSON object with:
    - specialist: The chosen specialist type
    - task_description: Clear task for the specialist
    - priority: Task priority level
    - context: Relevant context
    - reasoning: Explanation for the choice
    """

    return Task(
        description=task_description,
        expected_output=expected_output,
        agent=agent,
    )
