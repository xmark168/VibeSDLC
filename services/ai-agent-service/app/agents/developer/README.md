# Developer Agent

Main Developer Agent that orchestrates software development tasks using DeepAgents framework.

## Architecture

```
Developer Agent (Main DeepAgent) ← ONLY agent using create_deep_agent()
├── Implementor Subagent (prompt-based configuration)
│   ├── Tools: Codebase analysis, Git operations, code generation
│   └── Nested Subagents: code_generator, code_reviewer
└── Code Reviewer Subagent (prompt-based configuration)
    └── Tools: Read-only file access for review
```

### Key Principle

**ONLY `developer/agent.py` uses `create_deep_agent()`**

- `implementor/` exports subagent configuration (NOT a standalone agent)
- `code_reviewer/` exports subagent configuration (NOT a standalone agent)
- Main Developer Agent orchestrates both subagents via the `task` tool

## Usage

### Basic Usage

```python
from app.agents.developer import run_developer_agent

result = await run_developer_agent(
    user_request="Add user authentication with JWT tokens",
    working_directory="./src",
    model_name="gpt-4o"
)
```

### Advanced Usage

```python
from app.agents.developer import create_developer_agent

agent = create_developer_agent(
    working_directory="./src",
    model_name="gpt-4o",
    recursion_limit=500
)

result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Implement user profile API"}],
    "working_directory": "./src"
})
```

## Workflow

### Standard Development Flow

1. **User Request** → Main Developer Agent
2. **Planning** → Agent uses `write_todos` to create implementation plan
3. **Delegation to Implementor** → Agent uses `task` tool to delegate implementation
   ```python
   task(
       description="Implement user authentication with JWT",
       subagent_type="implementor"
   )
   ```
4. **Implementation** → Implementor subagent:
   - Analyzes codebase
   - Generates code
   - Creates feature branch
   - Commits changes
5. **Delegation to Code Reviewer** → Agent uses `task` tool to request review
   ```python
   task(
       description="Review authentication implementation for security",
       subagent_type="code_reviewer"
   )
   ```
6. **Review** → Code Reviewer subagent provides feedback
7. **Iteration** → If issues found, delegate back to Implementor for fixes
8. **Finalization** → Implementor creates pull request

## Subagents

### Implementor Subagent

**Location:** `implementor/`

**Purpose:** Handles feature implementation and code generation

**Capabilities:**
- Analyzes existing codebase structure
- Generates new code following best practices
- Modifies existing code
- Creates feature branches
- Commits changes to Git
- Creates pull requests
- Handles complete implementation workflow

**Tools Available:**
- `load_codebase_tool`: Analyze codebase structure
- `index_codebase_tool`: Index codebase with pgvector
- `search_similar_code_tool`: Semantic code search
- `sync_virtual_to_disk_tool`: Sync virtual FS to real disk
- `list_virtual_files_tool`: List files in virtual FS
- `detect_stack_tool`: Detect technology stack
- `retrieve_boilerplate_tool`: Get boilerplate templates
- `create_feature_branch_tool`: Create Git feature branch
- `select_integration_strategy_tool`: Choose integration approach
- ~~`generate_code_tool`~~: DEPRECATED - Use `task(subagent_type="code_generator")` instead
- `commit_changes_tool`: Commit to Git
- `create_pull_request_tool`: Create PR
- `collect_feedback_tool`: Collect user feedback
- `refine_code_tool`: Refine based on feedback

**Nested Subagents:**
- `code_generator`: Generates code based on specifications
- `code_reviewer`: Reviews generated code (internal to implementor)

### Code Reviewer Subagent

**Location:** `code_reviewer/`

**Purpose:** Reviews code for quality, security, and best practices

**Capabilities:**
- Reviews code quality and structure
- Identifies security vulnerabilities
- Checks performance implications
- Verifies best practices adherence
- Provides actionable feedback with severity levels

**Review Criteria:**
1. **Code Quality**: Readability, maintainability, structure
2. **Security**: Vulnerabilities, input validation, auth/authz
3. **Performance**: Algorithm efficiency, resource usage
4. **Best Practices**: Language conventions, design patterns
5. **Integration**: Compatibility with existing codebase

**Tools Available:**
- DeepAgents built-in: `read_file`, `ls` (read-only access)

## Configuration

### Environment Variables

```bash
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key
PGVECTOR_CONNECTION_STRING=postgresql://user:pass@host:port/db
```

### Parameters

- `working_directory`: Root directory for development tasks (default: ".")
- `model_name`: LLM model to use (default: "gpt-4o")
- `recursion_limit`: Maximum recursion depth (default: 500)

## Example Workflows

### Example 1: Add New Feature

```python
result = await run_developer_agent(
    user_request="""
    Add user profile feature to the API:
    - GET /api/profiles/me - Get current user profile
    - PUT /api/profiles/me - Update profile
    - Include fields: full_name, bio, avatar_url
    """,
    working_directory="./backend"
)
```

**What happens:**
1. Main agent creates todos for the feature
2. Delegates to implementor: "Implement profile endpoints"
3. Implementor analyzes existing API structure
4. Implementor generates code for profile endpoints
5. Main agent delegates to code_reviewer: "Review profile implementation"
6. Code reviewer checks security, quality, best practices
7. If issues found, main agent delegates back to implementor for fixes
8. Implementor commits changes and creates PR

### Example 2: Fix Security Issue

```python
result = await run_developer_agent(
    user_request="Fix SQL injection vulnerability in user search endpoint",
    working_directory="./backend"
)
```

**What happens:**
1. Main agent delegates to implementor: "Fix SQL injection in user search"
2. Implementor analyzes the vulnerable code
3. Implementor fixes the issue (parameterized queries)
4. Main agent delegates to code_reviewer: "Verify SQL injection fix"
5. Code reviewer confirms the fix is correct
6. Implementor commits the fix

## File Structure

```
developer/
├── __init__.py              # Exports create_developer_agent, run_developer_agent
├── agent.py                 # Main Developer Agent (ONLY create_deep_agent() call)
├── README.md                # This file
├── implementor/
│   ├── __init__.py          # Exports implementor_subagent configuration
│   ├── instructions.py      # Implementor prompt and workflow
│   ├── subagents.py         # Nested subagents (code_generator, code_reviewer)
│   ├── tools/               # Implementation tools
│   │   ├── codebase_tools.py
│   │   ├── git_tools.py
│   │   ├── generation_tools.py
│   │   └── sync_tools.py
│   └── README.md            # Implementor documentation
└── code_reviewer/
    ├── __init__.py          # Exports code_reviewer_subagent configuration
    ├── instructions.py      # Code review prompt and criteria
    └── README.md            # Code reviewer documentation
```

## Key Differences from Old Architecture

### Before (Multiple Standalone Agents)

```
❌ implementor/agent.py: create_deep_agent()  # Standalone agent
❌ code_reviewer/agent.py: create_deep_agent()  # Standalone agent
❌ No orchestration layer
```

### After (One Main Agent with Subagents)

```
✅ developer/agent.py: create_deep_agent()  # ONLY agent
✅ implementor/__init__.py: SubAgent config  # Subagent
✅ code_reviewer/__init__.py: SubAgent config  # Subagent
✅ Main agent orchestrates via task tool
```

## Benefits of New Architecture

1. **Single Entry Point**: One agent to rule them all
2. **Clear Orchestration**: Main agent coordinates workflow
3. **Better State Management**: Shared state across subagents
4. **Simplified Deployment**: One agent to deploy
5. **Consistent Interface**: Uniform API for all development tasks
6. **Easier Testing**: Test main agent with mocked subagents

## Testing

```python
import asyncio
from app.agents.developer import run_developer_agent

async def test_developer_agent():
    result = await run_developer_agent(
        user_request="Add health check endpoint",
        working_directory="./test_project"
    )
    print("Result:", result)

asyncio.run(test_developer_agent())
```

## Troubleshooting

### Import Errors

If you see import errors, ensure:
1. `developer/__init__.py` exists and exports `create_developer_agent`
2. `implementor/__init__.py` exports `implementor_subagent`
3. `code_reviewer/__init__.py` exports `code_reviewer_subagent`

### Subagent Not Found

If main agent can't find subagent:
1. Check subagent `name` field matches what main agent uses
2. Verify subagent is in `subagents` list in `create_developer_agent()`
3. Check DeepAgents version supports subagents

### Virtual FS Issues

If files aren't syncing to disk:
1. Ensure implementor calls `sync_virtual_to_disk_tool` before Git operations
2. Check `working_directory` is correct
3. Verify file permissions

## Contributing

When adding new capabilities:
1. Add tools to `implementor/tools/` if implementation-related
2. Update `implementor_subagent` tools list in `implementor/__init__.py`
3. Update instructions in `implementor/instructions.py`
4. Do NOT create new standalone agents - use subagents instead

## License

Internal use only - VibeSDLC project

