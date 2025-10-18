# app/agents/developer/implementor/tools/review_tools.py
"""
Code review and feedback tools
"""

import json
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
from datetime import datetime


@tool
def collect_feedback_tool(
    generated_code: str, implementation_summary: str, request_type: str = "review"
) -> str:
    """
    Collect user feedback on generated code.

    This tool presents the generated code to the user and collects
    their feedback for improvements or approval.

    Args:
        generated_code: The code that was generated
        implementation_summary: Summary of what was implemented
        request_type: Type of feedback request ("review", "approval", "specific")

    Returns:
        JSON string with user feedback and next steps

    Example:
        collect_feedback_tool(
            "def authenticate_user(username, password): ...",
            "Added user authentication function with JWT token generation",
            "review"
        )
    """
    try:
        # Format the code presentation
        feedback_request = {
            "action": "collect_feedback",
            "timestamp": datetime.now().isoformat(),
            "request_type": request_type,
            "implementation_summary": implementation_summary,
            "generated_code": generated_code,
            "feedback_questions": generate_feedback_questions(request_type),
            "review_criteria": get_review_criteria(),
            "user_prompt": create_user_feedback_prompt(
                generated_code, implementation_summary, request_type
            ),
        }

        return json.dumps(feedback_request, indent=2)

    except Exception as e:
        return f"Error collecting feedback: {str(e)}"


def generate_feedback_questions(request_type: str) -> List[str]:
    """Generate appropriate feedback questions based on request type"""

    base_questions = [
        "Does the generated code meet your requirements?",
        "Are there any issues with the implementation?",
        "Would you like any changes or improvements?",
    ]

    if request_type == "review":
        return base_questions + [
            "Is the code style consistent with your project?",
            "Are there any security concerns?",
            "Is the error handling appropriate?",
            "Are there any performance considerations?",
        ]
    elif request_type == "approval":
        return [
            "Do you approve this implementation?",
            "Should I proceed with committing these changes?",
            "Are there any final adjustments needed?",
        ]
    elif request_type == "specific":
        return base_questions + [
            "What specific aspects would you like me to focus on?",
            "Are there particular patterns or conventions to follow?",
            "Do you have specific requirements I should address?",
        ]
    else:
        return base_questions


def get_review_criteria() -> Dict[str, List[str]]:
    """Get standard code review criteria"""
    return {
        "functionality": [
            "Does the code solve the intended problem?",
            "Are all requirements addressed?",
            "Does it handle edge cases appropriately?",
        ],
        "code_quality": [
            "Is the code readable and well-structured?",
            "Are naming conventions consistent?",
            "Is the code properly documented?",
        ],
        "security": [
            "Are there any security vulnerabilities?",
            "Is input validation implemented?",
            "Are sensitive data handled properly?",
        ],
        "performance": [
            "Is the code efficient?",
            "Are there any performance bottlenecks?",
            "Is resource usage optimized?",
        ],
        "maintainability": [
            "Is the code easy to understand and modify?",
            "Are dependencies managed properly?",
            "Is the code testable?",
        ],
    }


def create_user_feedback_prompt(
    generated_code: str, implementation_summary: str, request_type: str
) -> str:
    """Create a user-friendly prompt for feedback collection"""

    prompt = f"""# CODE REVIEW REQUEST

## Implementation Summary
{implementation_summary}

## Generated Code
```
{generated_code[:2000]}{'...' if len(generated_code) > 2000 else ''}
```

## Feedback Request
"""

    if request_type == "review":
        prompt += """
Please review the generated code and provide feedback on:

1. **Functionality**: Does it meet your requirements?
2. **Code Quality**: Is it well-written and maintainable?
3. **Security**: Are there any security concerns?
4. **Performance**: Any performance considerations?
5. **Style**: Does it match your project conventions?

Please provide specific feedback or approve if satisfied.
"""

    elif request_type == "approval":
        prompt += """
Please review the implementation and let me know:

1. Do you approve this code for commit?
2. Are there any final changes needed?
3. Should I proceed with the next steps?

Type 'approve' to proceed or provide specific feedback for changes.
"""

    elif request_type == "specific":
        prompt += """
Please provide specific feedback on what you'd like me to focus on or change.
Be as detailed as possible about your requirements and preferences.
"""

    prompt += """

## Response Options
- **Approve**: Type 'approve' or 'looks good' to proceed
- **Request Changes**: Describe specific changes you'd like
- **Ask Questions**: Ask for clarification on any aspect

Your feedback will help me improve the implementation to better meet your needs.
"""

    return prompt


@tool
def refine_code_tool(
    original_code: str,
    user_feedback: str,
    implementation_context: str,
    refinement_focus: str = "general",
) -> str:
    """
    Refine code based on user feedback.

    This tool takes user feedback and uses it to improve the generated code,
    addressing specific concerns and requirements.

    Args:
        original_code: The original generated code
        user_feedback: Feedback from the user
        implementation_context: Context about the implementation
        refinement_focus: Specific area to focus on ("security", "performance", "style", "general")

    Returns:
        JSON string with refinement request for code_reviewer subagent

    Example:
        refine_code_tool(
            "def authenticate_user(username, password): ...",
            "Add input validation and better error handling",
            "User authentication function for FastAPI app",
            "security"
        )
    """
    try:
        # Parse and categorize feedback
        feedback_analysis = analyze_feedback(user_feedback)

        # Create refinement request
        refinement_request = {
            "action": "refine_code",
            "timestamp": datetime.now().isoformat(),
            "original_code": original_code,
            "user_feedback": user_feedback,
            "implementation_context": implementation_context,
            "refinement_focus": refinement_focus,
            "feedback_analysis": feedback_analysis,
            "subagent_required": "code_reviewer",
            "refinement_prompt": create_refinement_prompt(
                original_code,
                user_feedback,
                implementation_context,
                refinement_focus,
                feedback_analysis,
            ),
            "expected_improvements": generate_expected_improvements(feedback_analysis),
        }

        return json.dumps(refinement_request, indent=2)

    except Exception as e:
        return f"Error refining code: {str(e)}"


def analyze_feedback(user_feedback: str) -> Dict[str, Any]:
    """Analyze user feedback to categorize and prioritize changes"""

    feedback_lower = user_feedback.lower()

    analysis = {
        "sentiment": "neutral",
        "categories": [],
        "priority": "medium",
        "specific_requests": [],
        "approval_status": "pending",
    }

    # Determine approval status
    if any(
        word in feedback_lower
        for word in ["approve", "good", "looks good", "lgtm", "ship it"]
    ):
        analysis["approval_status"] = "approved"
        analysis["sentiment"] = "positive"
    elif any(
        word in feedback_lower for word in ["reject", "no", "not good", "needs work"]
    ):
        analysis["approval_status"] = "rejected"
        analysis["sentiment"] = "negative"

    # Categorize feedback
    categories = {
        "security": [
            "security",
            "validation",
            "sanitize",
            "vulnerability",
            "auth",
            "permission",
        ],
        "performance": [
            "performance",
            "slow",
            "optimize",
            "efficient",
            "speed",
            "memory",
        ],
        "style": ["style", "format", "naming", "convention", "readable", "clean"],
        "functionality": [
            "bug",
            "error",
            "wrong",
            "fix",
            "issue",
            "problem",
            "feature",
        ],
        "documentation": ["comment", "document", "explain", "unclear", "confusing"],
        "testing": ["test", "testing", "coverage", "unit test", "integration"],
    }

    for category, keywords in categories.items():
        if any(keyword in feedback_lower for keyword in keywords):
            analysis["categories"].append(category)

    # Determine priority
    if any(
        word in feedback_lower
        for word in ["critical", "urgent", "important", "must", "required"]
    ):
        analysis["priority"] = "high"
    elif any(
        word in feedback_lower
        for word in ["minor", "small", "nice to have", "optional"]
    ):
        analysis["priority"] = "low"

    # Extract specific requests (simplified)
    sentences = user_feedback.split(".")
    for sentence in sentences:
        sentence = sentence.strip()
        if any(
            word in sentence.lower()
            for word in ["add", "remove", "change", "fix", "improve", "update"]
        ):
            analysis["specific_requests"].append(sentence)

    return analysis


def create_refinement_prompt(
    original_code: str,
    user_feedback: str,
    implementation_context: str,
    refinement_focus: str,
    feedback_analysis: Dict[str, Any],
) -> str:
    """Create a detailed prompt for code refinement"""

    prompt = f"""# CODE REFINEMENT REQUEST

## Original Code
```
{original_code}
```

## User Feedback
{user_feedback}

## Implementation Context
{implementation_context}

## Refinement Focus
{refinement_focus}

## Feedback Analysis
- **Priority**: {feedback_analysis.get('priority', 'medium')}
- **Categories**: {', '.join(feedback_analysis.get('categories', []))}
- **Approval Status**: {feedback_analysis.get('approval_status', 'pending')}

## Specific Requests
"""

    for request in feedback_analysis.get("specific_requests", []):
        prompt += f"- {request}\n"

    prompt += f"""

## Refinement Instructions

Based on the user feedback, please refine the code to address the following:

"""

    if refinement_focus == "security":
        prompt += """
### Security Focus
- Add input validation and sanitization
- Implement proper error handling without information leakage
- Ensure secure authentication and authorization
- Address any security vulnerabilities
- Follow security best practices
"""

    elif refinement_focus == "performance":
        prompt += """
### Performance Focus
- Optimize algorithms and data structures
- Reduce memory usage and computational complexity
- Implement caching where appropriate
- Minimize database queries and API calls
- Profile and improve bottlenecks
"""

    elif refinement_focus == "style":
        prompt += """
### Style Focus
- Follow consistent naming conventions
- Improve code readability and structure
- Add appropriate comments and documentation
- Format code according to style guidelines
- Ensure consistent patterns throughout
"""

    else:
        prompt += """
### General Refinement
- Address all feedback points systematically
- Improve overall code quality
- Ensure functionality meets requirements
- Add appropriate error handling
- Follow best practices for the language/framework
"""

    prompt += """

## Output Requirements
Please provide:
1. **Refined Code**: Complete improved version
2. **Changes Made**: List of specific improvements
3. **Rationale**: Explanation for each change
4. **Testing Notes**: How to verify the improvements
5. **Additional Recommendations**: Any further suggestions

Ensure the refined code addresses all user feedback while maintaining or improving functionality.
"""

    return prompt


def generate_expected_improvements(feedback_analysis: Dict[str, Any]) -> List[str]:
    """Generate list of expected improvements based on feedback analysis"""

    improvements = []
    categories = feedback_analysis.get("categories", [])

    if "security" in categories:
        improvements.extend(
            [
                "Enhanced input validation",
                "Improved error handling",
                "Security vulnerability fixes",
            ]
        )

    if "performance" in categories:
        improvements.extend(
            [
                "Algorithm optimization",
                "Memory usage improvements",
                "Reduced computational complexity",
            ]
        )

    if "style" in categories:
        improvements.extend(
            [
                "Better code formatting",
                "Consistent naming conventions",
                "Improved readability",
            ]
        )

    if "functionality" in categories:
        improvements.extend(
            ["Bug fixes", "Feature enhancements", "Requirement compliance"]
        )

    if "documentation" in categories:
        improvements.extend(
            ["Better code comments", "Clearer documentation", "Usage examples"]
        )

    if "testing" in categories:
        improvements.extend(
            [
                "Test coverage improvements",
                "Better test cases",
                "Testing recommendations",
            ]
        )

    # Add general improvements if no specific categories
    if not improvements:
        improvements = [
            "Code quality improvements",
            "Best practices implementation",
            "General refinements based on feedback",
        ]

    return improvements
