"""
Code Reviewer Subagent Configuration

This module exports the Code Reviewer subagent configuration for the main Developer Agent.
The Code Reviewer is a subagent that analyzes generated code for quality, security, and best practices.

Architecture:
```
Developer Agent (Main DeepAgent)
└── Code Reviewer Subagent (this module)
    ├── Instructions: Code review guidelines and criteria
    └── Tools: Read-only access to virtual filesystem
```

## Subagent Configuration

The `code_reviewer_subagent` dict contains:
- **name**: "code_reviewer"
- **description**: When to use this subagent
- **prompt**: Complete instructions for code review process
- **tools**: Minimal tools (mainly read_file from DeepAgents)

## Usage

This subagent is used by the main Developer Agent:

```python
from app.agents.developer import create_developer_agent

# Main agent automatically includes code_reviewer subagent
agent = create_developer_agent(working_directory="./src")

# Main agent delegates to code_reviewer:
result = await agent.ainvoke({
    "messages": [{
        "role": "user", 
        "content": "Review the authentication implementation"
    }]
})
```

## Review Criteria

The Code Reviewer evaluates:
1. **Code Quality**: Readability, maintainability, structure
2. **Security**: Vulnerabilities, input validation, auth/authz
3. **Performance**: Algorithm efficiency, resource usage
4. **Best Practices**: Language conventions, design patterns
5. **Integration**: Compatibility with existing codebase
"""

from deepagents.types import SubAgent
from .instructions import get_code_reviewer_instructions

# Code Reviewer Subagent Configuration
code_reviewer_subagent: SubAgent = {
    "name": "code_reviewer",
    "description": (
        "Expert code reviewer that analyzes generated code for quality, security, "
        "and best practices. Use this subagent when you need to: "
        "(1) Review code before committing, "
        "(2) Identify security vulnerabilities, "
        "(3) Check performance implications, "
        "(4) Verify adherence to coding standards, "
        "(5) Provide actionable feedback for improvements. "
        "The reviewer has read-only access to files and provides detailed analysis."
    ),
    "prompt": get_code_reviewer_instructions(),
    "tools": [],  # Uses DeepAgents' built-in read_file, ls tools
}

__all__ = ["code_reviewer_subagent"]

