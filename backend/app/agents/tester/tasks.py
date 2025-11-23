"""Tester task definitions.

Tasks for QA planning, test case creation, and quality assurance.
"""

from typing import Any, Dict

from crewai import Agent, Task


def create_test_plan_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for generating a comprehensive test plan.

    Args:
        agent: Tester agent
        context: Context containing task_description

    Returns:
        CrewAI Task for test plan creation
    """
    task_description = context.get("task_description", "")
    additional_context = context.get("additional_context", "")
    user_message = context.get("user_message", "")

    description = f"""
    Create a comprehensive test plan for the following feature or requirement:

    Original Request: {user_message}

    Task Assignment: {task_description}

    Additional Context: {additional_context}

    Create a detailed test plan including:

    1. **Test Strategy Overview**
       - Testing approach (risk-based, requirement-based, etc.)
       - Test levels (unit, integration, E2E, acceptance)
       - Testing types (functional, performance, security, usability)
       - In scope vs out of scope

    2. **Test Cases**
       For each test case, provide:
       - Test Case ID (TC-001, TC-002, etc.)
       - Title
       - Description
       - Preconditions
       - Test Steps (numbered list)
       - Expected Results
       - Priority (High/Medium/Low)
       - Type (Positive/Negative/Edge Case)

       Include at least:
       - 3-5 positive test cases (happy path)
       - 2-3 negative test cases (error scenarios)
       - 2-3 edge cases (boundary conditions)

    3. **Test Data Requirements**
       - What test data is needed
       - Data setup instructions
       - Data cleanup procedures
       - Mock data specifications

    4. **Automation Recommendations**
       - Which tests should be automated
       - Suggested automation framework
       - Priority for automation
       - ROI considerations

    5. **Risk Assessment**
       - High-risk areas requiring extra testing
       - Dependencies and blockers
       - Testing challenges
       - Mitigation strategies

    6. **Success Criteria**
       - Pass/Fail conditions
       - Quality metrics
       - Coverage goals
       - Performance benchmarks

    7. **Test Environment Requirements**
       - Environment setup
       - Tools needed
       - Access requirements
       - Data requirements

    Format as a professional test plan document ready for execution.
    """

    expected_output = """
    A comprehensive test plan containing:
    - Test strategy and approach
    - Detailed test cases with steps (8-10 cases minimum)
    - Test data requirements
    - Automation recommendations
    - Risk assessment
    - Success criteria
    - Environment requirements
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )


def create_validate_requirements_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for validating implementation against requirements.

    Args:
        agent: Tester agent
        context: Context containing implementation details

    Returns:
        CrewAI Task for validation
    """
    task_description = context.get("task_description", "")
    additional_context = context.get("additional_context", "")

    description = f"""
    Validate the following against requirements:

    What to Validate: {task_description}

    Context: {additional_context}

    Provide a comprehensive validation report:

    1. **Compliance Check**
       - Does the implementation meet the requirements?
       - List each requirement and its status (Met/Partial/Not Met)
       - Gaps identified

    2. **Edge Cases Analysis**
       - Boundary conditions to test
       - Error scenarios to verify
       - Unusual user behaviors

    3. **Security Testing Points**
       - Authentication/Authorization checks
       - Input validation
       - Data protection
       - OWASP top 10 considerations

    4. **Performance Considerations**
       - Load testing requirements
       - Response time expectations
       - Scalability concerns
       - Resource usage

    5. **User Acceptance Criteria**
       - User workflow validation
       - Usability concerns
       - Accessibility requirements
       - User experience feedback

    6. **Recommendations**
       - Areas needing improvement
       - Additional testing needed
       - Sign-off readiness

    Format as a professional validation report.
    """

    expected_output = """
    A validation report with:
    - Compliance analysis
    - Edge cases identified
    - Security testing points
    - Performance considerations
    - User acceptance criteria
    - Recommendations
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )


def create_test_cases_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """Create task for generating specific test cases.

    Args:
        agent: Tester agent
        context: Context containing feature details

    Returns:
        CrewAI Task for test case generation
    """
    task_description = context.get("task_description", "")
    additional_context = context.get("additional_context", "")

    description = f"""
    Generate detailed test cases for:

    Feature: {task_description}

    Context: {additional_context}

    For each test case, provide:

    **Test Case Format:**
    ```
    Test Case ID: TC-XXX
    Title: [Brief descriptive title]
    Priority: High / Medium / Low
    Type: Positive / Negative / Edge Case / Security / Performance

    Description:
    [What this test verifies]

    Preconditions:
    - [List setup requirements]

    Test Steps:
    1. [Action]
    2. [Action]
    3. [Action]

    Expected Results:
    - [What should happen]
    - [Verification points]

    Test Data:
    - [Required data]

    Notes:
    - [Any special considerations]
    ```

    Generate at least 10 test cases covering:
    - Happy path scenarios (4-5 cases)
    - Error/failure scenarios (3-4 cases)
    - Edge cases and boundaries (2-3 cases)
    - Security scenarios (1-2 cases)

    Prioritize based on business impact and risk.
    """

    expected_output = """
    A collection of 10+ detailed test cases in standard format, covering:
    - Positive scenarios
    - Negative scenarios
    - Edge cases
    - Security scenarios
    Each with clear steps, expected results, and test data.
    """

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )
