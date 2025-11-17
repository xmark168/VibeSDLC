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
    Analyze the following user message and determine which specialist should handle it:

    User Message: {user_message}

    Available specialists:
    - business_analyst: For requirements analysis, PRD creation, user stories, acceptance criteria
    - developer: For code implementation, technical solutions, architecture design, bug fixes
    - tester: For QA planning, test cases, validation, quality assurance, testing strategies

    Analyze the message carefully and decide:
    1. Which specialist is best suited for this task
    2. What specific task should they perform
    3. What context they need to complete the task

    Consider these keywords:
    - Business Analyst: "requirements", "user story", "PRD", "acceptance criteria", "features", "needs", "analyze"
    - Developer: "implement", "code", "build", "create", "develop", "fix bug", "architecture"
    - Tester: "test", "QA", "validate", "quality", "coverage", "test plan", "test cases"

    Respond ONLY with a valid JSON object (no markdown, no code blocks):
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
