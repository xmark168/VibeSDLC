"""
Implementor Subagent Configuration

This module exports the Implementor subagent configuration for the main Developer Agent.
The Implementor is NO LONGER a standalone DeepAgent - it's a subagent that handles
feature implementation and code generation tasks.

Architecture:
```
Developer Agent (Main DeepAgent)
└── Implementor Subagent (this module)
    ├── Instructions: Implementation workflow and guidelines
    ├── Tools: Codebase analysis, Git operations, code generation
    └── Nested Subagents: code_generator, code_reviewer
```

## Subagent Configuration

The `implementor_subagent` dict contains:
- **name**: "implementor"
- **description**: When to use this subagent
- **prompt**: Complete instructions for implementation workflow
- **tools**: Tools available to this subagent

## Usage

This subagent is used by the main Developer Agent:

```python
from app.agents.developer import create_developer_agent

# Main agent automatically includes implementor subagent
agent = create_developer_agent(working_directory="./src")

# Main agent delegates to implementor:
result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Implement user auth"}]
})
```

## Tools Available to Implementor

- **Codebase Analysis**: load_codebase, index_codebase, search_similar_code
- **Stack Detection**: detect_stack, retrieve_boilerplate
- **Git Operations**: create_feature_branch, commit_changes, create_pull_request
- **Code Generation**: select_integration_strategy, generate_code
- **Feedback**: collect_feedback, refine_code
- **Virtual FS Sync**: sync_virtual_to_disk, list_virtual_files

## Nested Subagents

The Implementor subagent has its own subagents:
- **code_generator**: Generates code based on specifications
- **code_reviewer**: Reviews code for quality and security
"""

from deepagents.types import SubAgent
from .instructions import get_implementor_instructions
from .tools import (
    load_codebase_tool,
    index_codebase_tool,
    search_similar_code_tool,
    sync_virtual_to_disk_tool,
    list_virtual_files_tool,
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
from .subagents import code_generator_subagent

# Implementor Subagent Configuration
implementor_subagent: SubAgent = {
    "name": "implementor",
    "description": (
        "Expert implementor that handles feature implementation and code generation. "
        "Use this subagent when you need to: "
        "(1) Implement new features or functionality, "
        "(2) Generate or modify code, "
        "(3) Analyze existing codebase structure, "
        "(4) Create feature branches and commit changes, "
        "(5) Handle the complete implementation workflow from analysis to PR creation. "
        "The implementor has access to codebase analysis tools, Git operations, "
        "and nested subagents for code generation and review."
    ),
    "prompt": get_implementor_instructions(
        working_directory=".",  # Will be overridden by main agent
        project_type="new",
        enable_pgvector=False,
    ),
    "tools": [
        # Codebase analysis tools
        load_codebase_tool,
        index_codebase_tool,
        search_similar_code_tool,
        # Virtual FS sync tools (CRITICAL for Git workflow)
        sync_virtual_to_disk_tool,
        list_virtual_files_tool,
        # Stack detection & boilerplate
        detect_stack_tool,
        retrieve_boilerplate_tool,
        # Git operations
        create_feature_branch_tool,
        commit_changes_tool,
        create_pull_request_tool,
        # Code generation & strategy
        select_integration_strategy_tool,
        generate_code_tool,
        # Review & feedback
        collect_feedback_tool,
        refine_code_tool,
    ],
    # Nested subagents for specialized tasks
    # Note: DeepAgents doesn't support nested subagents in SubAgent type yet
    # So we include these in the tools list instead
}

# Export tools for use by main Developer Agent if needed
__all__ = [
    "implementor_subagent",
    "load_codebase_tool",
    "index_codebase_tool",
    "search_similar_code_tool",
    "sync_virtual_to_disk_tool",
    "list_virtual_files_tool",
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
]
