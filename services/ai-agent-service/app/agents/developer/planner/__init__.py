# app/agents/developer/planner/__init__.py
"""
Planner Agent using DeepAgents

A simplified, high-level implementation of the planner agent using DeepAgents
instead of manual LangGraph construction.

## Key Advantages over LangGraph Version

1. **Simpler**: No manual graph construction or routing logic
2. **More Maintainable**: DeepAgents handles workflow automatically
3. **Better Abstraction**: Focus on instructions and tools, not graph details
4. **Subagent Support**: Built-in support for specialized sub-tasks
5. **Proven Patterns**: Based on Claude Code and OpenSWE architecture

## Architecture

```
Main Agent (Planner)
├── Instructions: System prompt defining behavior
├── Tools: Read-only context gathering tools
│   ├── grep_search
│   ├── view_file
│   ├── shell_execute
│   ├── list_directory
│   └── take_notes
└── Subagents: Specialized agents for specific tasks
    ├── planGenerator: Creates implementation plans
    └── noteTaker: Condenses context into notes
```

## Usage

### Basic Usage

```python
from app.agents.developer.planner import run_planner

result = await run_planner(
    user_request="Add user authentication with JWT",
    working_directory="./src"
)

print(result['proposed_plan'])
```

### Advanced Usage

```python
from app.agents.developer.planner import create_planner_agent

agent = create_planner_agent(
    working_directory="./src",
    custom_rules={"general_rules": "Follow PEP 8"},
    codebase_tree="src/\\n  auth/\\n  models/",
    model_name="gpt-4"
)

result = await agent.ainvoke(initial_state, config)
```

## Workflow

DeepAgents automatically handles the workflow:

1. **Context Gathering**: Agent uses tools to explore codebase
2. **Note Taking**: Agent records findings with take_notes tool
3. **Plan Generation**: Agent invokes planGenerator subagent
4. **Note Condensing**: Agent invokes noteTaker subagent
5. **Return Results**: Final plan and notes are returned

No manual graph construction or routing logic required!

## Comparison with LangGraph Version

| Aspect | LangGraph | DeepAgents |
|--------|-----------|------------|
| Lines of Code | ~1500 | ~600 |
| Complexity | High (manual graph) | Low (declarative) |
| Workflow | Manual routing | Automatic |
| Subagents | Manual integration | Built-in |
| Maintenance | Complex | Simple |
| Flexibility | Very high | High |

## When to Use Which

**Use DeepAgents (this version) when:**
- You want simplicity and maintainability
- Standard workflow patterns are sufficient
- You trust the framework to handle routing
- You want to focus on behavior, not structure

**Use LangGraph when:**
- You need fine-grained control over workflow
- You have complex conditional routing
- You need custom node implementations
- You want to see every state transition

## Installation

```bash
pip install deepagents langchain langchain-openai pydantic
```

## Environment Variables

```bash
OPENAI_API_KEY=your-key
# OR
ANTHROPIC_API_KEY=your-key
```
"""

from .agent import create_planner_agent, run_planner
from .state import PlannerAgentState, PlannerState
from .tools import (
    grep_search_tool,
    view_file_tool,
    shell_execute_tool,
    list_directory_tool,
    take_notes_tool,
    get_scratchpad_notes,
)
from .subagents import plan_generator_subagent, note_taker_subagent
from .instructions import get_planner_instructions

__all__ = [
    # Main API
    "create_planner_agent",
    "run_planner",
    # State
    "PlannerAgentState",
    "PlannerState",
    # Tools
    "grep_search_tool",
    "view_file_tool",
    "shell_execute_tool",
    "list_directory_tool",
    "take_notes_tool",
    "get_scratchpad_notes",
    # Subagents
    "plan_generator_subagent",
    "note_taker_subagent",
    # Instructions
    "get_planner_instructions",
]

__version__ = "2.0.0"  # DeepAgents version
