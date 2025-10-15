"""
Code Implementor Agent using DeepAgents

This agent implements features based on user requirements using the deepagents library.
It replaces the separate planner subagent by leveraging deepagents' built-in planning capabilities.

Key Features:
- Built-in planning with write_todos tool
- Stack detection and boilerplate retrieval
- pgvector indexing for codebase context
- Automated workflow with todo management
- Git operations (branch, commit, PR)
- Code generation with subagents
- User feedback and refinement loop

Architecture:
```
Main Agent (Implementor)
├── Instructions: System prompt defining behavior
├── Tools: Implementation and context tools
│   ├── load_codebase
│   ├── index_codebase (pgvector)
│   ├── detect_stack
│   ├── retrieve_boilerplate
│   ├── create_feature_branch
│   ├── select_integration_strategy
│   ├── generate_code
│   ├── commit_changes
│   ├── create_pull_request
│   ├── collect_feedback
│   └── refine_code
└── Subagents: Specialized agents for specific tasks
    ├── code_generator: Generates code based on strategy
    └── code_reviewer: Reviews generated code for quality
```

## Usage

### Basic Usage

```python
from app.agents.developer.implementor import run_implementor

result = await run_implementor(
    user_request="Add user authentication with JWT",
    working_directory="./src",
    project_type="new"  # or "existing"
)
```

### Advanced Usage

```python
from app.agents.developer.implementor import create_implementor_agent

agent = create_implementor_agent(
    working_directory="./src",
    enable_pgvector=True,
    boilerplate_templates_path="./templates/boilerplate"
)

result = await agent.ainvoke(initial_state, config)
```

## Workflow

DeepAgents automatically handles the workflow:

1. **Planning**: Agent uses write_todos to create implementation plan
2. **Codebase Analysis**: Load and index existing codebase with pgvector
3. **Stack Detection**: For new projects, detect stack and retrieve boilerplate
4. **Implementation Loop**: For each todo task:
   - Select integration strategy
   - Generate code using subagents
   - Commit changes
   - Update todo status
5. **Review & Refinement**: Handle user feedback and code improvements
6. **Completion**: Create pull request when all tasks completed

No manual graph construction or routing logic required!

## Integration Strategies

- **extend_existing**: Add to existing files/classes
- **create_new**: Create new files/modules
- **refactor**: Restructure existing code
- **fix_issue**: Fix bugs or issues
- **hybrid**: Combination approach (not recommended)

## Requirements

- deepagents>=0.0.10
- pgvector database for indexing
- Git repository for version control
- Boilerplate templates in templates/boilerplate/

## Environment Variables

```bash
OPENAI_API_KEY=your-key
PGVECTOR_CONNECTION_STRING=postgresql://user:pass@host:port/db
BOILERPLATE_TEMPLATES_PATH=./templates/boilerplate
```
"""

from .agent import create_implementor_agent, run_implementor
from .tools import (
    load_codebase_tool,
    index_codebase_tool,
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

__all__ = [
    "create_implementor_agent",
    "run_implementor",
    "load_codebase_tool",
    "index_codebase_tool", 
    "detect_stack_tool",
    "retrieve_boilerplate_tool",
    "create_feature_branch_tool",
    "select_integration_strategy_tool",
    "generate_code_tool",
    "commit_changes_tool",
    "create_pull_request_tool",
    "collect_feedback_tool",
    "refine_code_tool",
    "code_generator_subagent",
    "code_reviewer_subagent",
]
