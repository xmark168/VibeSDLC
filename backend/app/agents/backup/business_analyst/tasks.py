"""Business Analyst task definitions.

Tasks for requirements analysis, PRD creation, and user story writing.
"""

from typing import Any, Dict

from crewai import Agent, Task


def create_analyze_requirements_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for analyzing requirements and creating user stories.

    Args:
        agent: Business Analyst agent
        context: Context containing task_description and additional_context

    Returns:
        CrewAI Task for requirements analysis
    """
    task_description = context.get("task_description", "")
    additional_context = context.get("additional_context", "")
    user_message = context.get("user_message", "")

    description = f"""
    Analyze the following user requirement and create comprehensive documentation:

    Original User Message: {user_message}

    Task Assignment: {task_description}

    Additional Context: {additional_context}

    Create a detailed requirements analysis including:

    1. **User Story** in standard format:
       "As a [user type], I want [goal] so that [benefit]"

    2. **Acceptance Criteria** using Given/When/Then format:
       - Given [precondition]
       - When [action]
       - Then [expected result]
       (Include at least 3-5 acceptance criteria)

    3. **Story Points Estimate**: Use Fibonacci scale (1, 2, 3, 5, 8, 13)
       - 1: Trivial task, few hours
       - 2: Simple task, less than a day
       - 3: Standard task, 1-2 days
       - 5: Complex task, 3-5 days
       - 8: Very complex, up to a week
       - 13: Epic-level, needs breakdown

    4. **Dependencies or Assumptions**:
       List any technical or business dependencies

    5. **Risks or Concerns**:
       Identify potential issues or blockers

    6. **Priority Recommendation**:
       High / Medium / Low with justification

    Format your response as a structured document that can be directly used by the development team.
    """

    expected_output = """
    A comprehensive requirements document containing:
    - Well-formatted user story
    - Clear acceptance criteria (3-5 criteria)
    - Story point estimate with justification
    - Dependencies and assumptions
    - Risk analysis
    - Priority recommendation
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )


def create_prd_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for generating a Product Requirements Document.

    Args:
        agent: Business Analyst agent
        context: Context containing task_description

    Returns:
        CrewAI Task for PRD creation
    """
    task_description = context.get("task_description", "")
    additional_context = context.get("additional_context", "")

    description = f"""
    Create a comprehensive Product Requirements Document (PRD) for:

    Feature Request: {task_description}
    Context: {additional_context}

    The PRD should include the following sections:

    1. **Executive Summary** (2-3 paragraphs)
       - High-level overview of the feature
       - Business justification
       - Expected impact

    2. **Problem Statement**
       - What problem does this solve?
       - Who is affected?
       - Current pain points

    3. **Goals and Objectives**
       - Primary goals (3-5 bullet points)
       - Success metrics
       - Key results

    4. **User Stories** (3-5 stories)
       - Each in "As a..., I want..., so that..." format
       - With acceptance criteria
       - Priority (P0, P1, P2)

    5. **Functional Requirements**
       - Core functionality
       - User workflows
       - Edge cases

    6. **Non-Functional Requirements**
       - Performance expectations
       - Security considerations
       - Scalability needs

    7. **Technical Constraints**
       - Technology stack limitations
       - Integration requirements
       - Data considerations

    8. **Timeline Recommendations**
       - Estimated development time
       - Suggested milestones
       - Dependencies

    9. **Out of Scope**
       - What is NOT included
       - Future considerations

    Format as a professional PRD document suitable for stakeholder review.
    """

    expected_output = """
    A complete PRD document with all sections:
    - Executive Summary
    - Problem Statement
    - Goals and Objectives
    - User Stories with acceptance criteria
    - Functional and Non-Functional Requirements
    - Technical Constraints
    - Timeline Recommendations
    - Out of Scope items
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )
