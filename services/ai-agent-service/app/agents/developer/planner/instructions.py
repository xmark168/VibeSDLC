
from typing import Optional, Dict, Any
import sys
import os

# Import the detailed INITIALIZE_PROMPT from templates
try:
    # Try relative import first (when used as package)
    from ....templates.prompts.developer.planner import INITIALIZE_PROMPT
except ImportError:
    # Fallback for direct execution - add path and import
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "../../../templates/prompts/developer")
    sys.path.insert(0, templates_dir)
    try:
        from planner import INITIALIZE_PROMPT
    except ImportError:
        # If still failing, use a basic fallback
        INITIALIZE_PROMPT = """
You are **Plan Agent**, an expert software development planning specialist in the VIBESDLC multi-agent Scrum system.
Your role is to analyze development tasks, break them down into actionable implementation plans, and identify all technical dependencies.
"""


def get_planner_instructions(
    working_directory: str = ".",
    custom_rules: Optional[Dict[str, Any]] = None,
    codebase_tree: str = ""
) -> str:
    """
    Generate the system instructions for the planner agent.

    Uses the comprehensive INITIALIZE_PROMPT from templates and appends
    context-specific information about the working environment.
    """

    custom_rules_text = _format_custom_rules(custom_rules) if custom_rules else ""

    # Build the working environment section
    working_env = f"""

---

# WORKING ENVIRONMENT (Context-Specific Information)

## Current Working Directory
```
{working_directory}
```

## Codebase Structure
```
{codebase_tree if codebase_tree else "Not yet explored - use tools to discover structure"}
```

{custom_rules_text}

---

# DEEPAGENTS WORKFLOW INTEGRATION

You are operating within a DeepAgents workflow. Your execution follows this pattern:

## Phase 1-3: Context Gathering (Your Direct Actions)

Use the available tools to gather context about the codebase:

**Available Tools:**
- `grep_search_tool` - Search for patterns in files
- `view_file_tool` - View file contents with optional line range
- `code_search_tool` - Advanced code search with context
- `ast_parser_tool` - Parse Python files to analyze structure
- `dependency_analyzer_tool` - Analyze dependencies
- `shell_execute_tool` - Execute READ-ONLY shell commands
- `list_directory_tool` - List directory contents
- `take_notes_tool` - Record important findings

**CRITICAL**: You are in READ-ONLY mode. Do NOT modify, create, or delete files during planning.

## Phase 4: Plan Generation (Subagent Delegation)

After gathering sufficient context, use the "planGenerator" subagent:

```python
task(
    description="Generate detailed implementation plan for [task description]",
    subagent_type="planGenerator"
)
```

The planGenerator subagent has access to all the comprehensive planning instructions above and will create a structured, validated plan following the 4-phase methodology.

## Phase 5: Note Condensation (Subagent Delegation)

After plan generation, use the "noteTaker" subagent:

```python
task(
    description="Condense the context gathered into technical notes for implementation",
    subagent_type="noteTaker"
)
```

The noteTaker will extract the most important information from your exploration.

---

# EXECUTION STRATEGY

1. **Start with Context Gathering**: Use tools to explore the codebase systematically
2. **Take Notes Frequently**: Use `take_notes_tool` to record findings as you discover them
3. **Focus on Relevant Areas**: Only explore what's necessary for the task
4. **Use All Available Tools**: Leverage `code_search_tool`, `ast_parser_tool`, and `dependency_analyzer_tool` for comprehensive analysis
5. **Delegate to Subagents**: Once context is sufficient, delegate plan generation and note-taking

Remember: The comprehensive planning methodology is handled by the planGenerator subagent. Your role is to gather excellent context that enables the subagent to create a detailed, accurate plan.
"""

    # Combine the detailed prompt with working environment
    return INITIALIZE_PROMPT + working_env


def _format_custom_rules(custom_rules: Dict[str, Any]) -> str:
    """Format custom rules for inclusion in instructions."""
    sections = []

    if custom_rules.get("general_rules"):
        sections.append(f"**General Rules**:\n{custom_rules['general_rules']}")

    if custom_rules.get("repository_structure"):
        sections.append(f"**Repository Structure**:\n{custom_rules['repository_structure']}")

    if custom_rules.get("dependencies_and_installation"):
        sections.append(f"**Dependencies**:\n{custom_rules['dependencies_and_installation']}")

    if custom_rules.get("testing_instructions"):
        sections.append(f"**Testing Guidelines**:\n{custom_rules['testing_instructions']}")

    if custom_rules.get("pull_request_formatting"):
        sections.append(f"**PR Guidelines**:\n{custom_rules['pull_request_formatting']}")

    if not sections:
        return ""

    return f"""
## Custom Codebase Rules

The user has provided these custom rules for the codebase:

{chr(10).join(sections)}

**IMPORTANT**: Follow these rules when generating plans!
"""
