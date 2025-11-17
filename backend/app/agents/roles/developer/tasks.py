"""Developer task definitions.

Tasks for code implementation, architecture design, and technical solutions.
"""

from typing import Any, Dict

from crewai import Agent, Task


def create_implement_feature_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for implementing a feature or technical solution.

    Args:
        agent: Developer agent
        context: Context containing task_description and additional_context

    Returns:
        CrewAI Task for feature implementation
    """
    task_description = context.get("task_description", "")
    additional_context = context.get("additional_context", "")
    user_message = context.get("user_message", "")

    description = f"""
    Implement the following feature or technical solution:

    Original User Request: {user_message}

    Task Assignment: {task_description}

    Additional Context: {additional_context}

    Provide a comprehensive implementation including:

    1. **Architecture Overview**
       - How components fit together
       - Design patterns used
       - Data flow diagram (in text)

    2. **File Structure**
       - Which files need to be created
       - Which files need to be modified
       - Directory organization

    3. **Implementation Code**
       - Actual code with inline comments
       - Use proper naming conventions
       - Follow best practices for the language/framework

    4. **API Endpoints** (if applicable)
       - Endpoint definitions
       - Request/Response schemas
       - Authentication requirements

    5. **Database Changes** (if applicable)
       - Schema modifications
       - Migration scripts
       - Indexing considerations

    6. **Testing Recommendations**
       - Unit test suggestions
       - Integration test scenarios
       - Edge cases to cover

    7. **Potential Issues and Solutions**
       - Known limitations
       - Performance considerations
       - Security concerns
       - Error handling strategies

    8. **Deployment Notes**
       - Environment variables needed
       - Dependencies to install
       - Configuration changes

    Format your response as a structured technical document with clear code blocks.
    """

    expected_output = """
    A comprehensive implementation document containing:
    - Architecture overview and design decisions
    - Complete file structure
    - Implementationcode with comments
    - API and database specifications
    - Testing recommendations
    - Potential issues and mitigations
    - Deployment notes
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )


def create_code_review_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for reviewing code.

    Args:
        agent: Developer agent
        context: Context containing code_snippet

    Returns:
        CrewAI Task for code review
    """
    code_snippet = context.get("code_snippet", context.get("additional_context", ""))
    task_description = context.get("task_description", "")

    description = f"""
    Review the following code and provide detailed feedback:

    Review Task: {task_description}

    Code to Review:
    ```
    {code_snippet}
    ```

    Provide a comprehensive code review including:

    1. **Code Quality Assessment**
       - Readability and clarity
       - Code organization
       - Naming conventions
       - Comments and documentation

    2. **Security Concerns**
       - Input validation
       - SQL injection risks
       - XSS vulnerabilities
       - Authentication/Authorization issues
       - Data exposure risks

    3. **Performance Issues**
       - Inefficient algorithms
       - Database query optimization
       - Memory leaks
       - Caching opportunities

    4. **Best Practice Violations**
       - SOLID principles
       - DRY violations
       - Error handling
       - Logging practices

    5. **Suggested Improvements**
       - Specific code examples
       - Refactoring recommendations
       - Alternative approaches

    6. **Overall Rating**
       - Severity: Critical / High / Medium / Low
       - Recommendation: Approve / Request Changes / Reject

    Format your feedback clearly with code examples where applicable.
    """

    expected_output = """
    A detailed code review with:
    - Quality assessment
    - Security analysis
    - Performance evaluation
    - Best practice review
    - Actionable suggestions with examples
    - Overall rating and recommendation
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )


def create_bug_fix_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for fixing bugs.

    Args:
        agent: Developer agent
        context: Context containing bug description

    Returns:
        CrewAI Task for bug fixing
    """
    task_description = context.get("task_description", "")
    additional_context = context.get("additional_context", "")

    description = f"""
    Fix the following bug:

    Bug Description: {task_description}

    Additional Context: {additional_context}

    Provide:

    1. **Root Cause Analysis**
       - What is causing the bug?
       - Why did it happen?
       - Related code sections

    2. **Fix Implementation**
       - Code changes needed
       - Files to modify
       - Actual fix code

    3. **Testing Plan**
       - How to verify the fix
       - Test cases to add
       - Regression testing

    4. **Prevention**
       - How to prevent similar bugs
       - Code review checkpoints
       - Monitoring/alerting

    Format with clear code blocks and explanations.
    """

    expected_output = """
    Bug fix document with:
    - Root cause analysis
    - Implementation code
    - Testing plan
    - Prevention strategies
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )
