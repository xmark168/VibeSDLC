"""
Developer Agent Module

This module provides the main Developer Agent that orchestrates software development tasks.

Architecture:
```
Developer Agent (Main DeepAgent) - ONLY agent using create_deep_agent()
├── Implementor Subagent - Handles implementation and code generation
└── Code Reviewer Subagent - Reviews code for quality and security
```

## Usage

```python
from app.agents.developer import create_developer_agent, run_developer_agent

# Create agent
agent = create_developer_agent(
    working_directory="./src",
    model_name="gpt-4o"
)

# Run agent
result = await run_developer_agent(
    user_request="Add user authentication",
    working_directory="./src"
)
```

## Key Principle

**ONLY `developer/agent.py` uses `create_deep_agent()`**

- `implementor/` exports subagent configuration (not a standalone agent)
- `code_reviewer/` exports subagent configuration (not a standalone agent)
- Main Developer Agent orchestrates both subagents

## Subagents

### Implementor Subagent
- Analyzes codebase structure
- Generates and modifies code
- Handles Git operations (branch, commit, PR)
- Has access to specialized tools and nested subagents

### Code Reviewer Subagent
- Reviews code quality and structure
- Identifies security vulnerabilities
- Checks performance implications
- Provides actionable feedback
"""
