# Developer Planner Subagent

Planner subagent chịu trách nhiệm phân tích task requirements và tạo detailed implementation plan cho implementor subagent. Sử dụng LangGraph framework với 4-phase planning process.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Product       │    │     Planner      │    │   Implementor   │
│   Backlog       │───▶│    Subagent      │───▶│   Subagent      │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Code Reviewer   │
                       │    Subagent      │
                       └──────────────────┘
```

## 4-Phase Planning Process

### Phase 1: Task Parsing
- Extract functional requirements
- Identify acceptance criteria
- Parse business rules and constraints
- Extract technical specifications

### Phase 2: Codebase Analysis
- Analyze existing code patterns
- Identify files to create/modify
- Map affected modules and dependencies
- Assess database and API changes

### Phase 3: Dependency Mapping
- Create execution order
- Identify blocking relationships
- Find parallel execution opportunities
- Map internal and external dependencies

### Phase 4: Implementation Planning
- Calculate complexity score (1-10)
- Create detailed implementation steps
- Estimate effort (hours and story points)
- Identify risks and assumptions

## Directory Structure

```
planner/
├── __init__.py              # Main exports
├── agent.py                 # PlannerAgent class with LangGraph workflow
├── state.py                 # State management with Pydantic models
├── nodes/                   # Workflow nodes
│   ├── __init__.py
│   ├── initialize.py        # Setup and validation
│   ├── parse_task.py        # Phase 1: Task parsing
│   ├── analyze_codebase.py  # Phase 2: Codebase analysis
│   ├── map_dependencies.py  # Phase 3: Dependency mapping
│   ├── generate_plan.py     # Phase 4: Implementation planning
│   ├── validate_plan.py     # Plan validation with retry
│   └── finalize.py          # Final output preparation
├── tools/                   # Analysis tools
│   ├── __init__.py
│   ├── code_analysis.py     # Code search, AST parsing, file analysis
│   ├── dependency_tools.py  # Dependency analysis, execution order
│   └── planning_tools.py    # Task parsing, effort estimation, risk assessment
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── prompts.py          # System prompts for each phase
│   └── validators.py       # Plan validation logic
├── test_planner.py         # Test suite
└── README.md               # This file
```

## Key Components

### PlannerState
Comprehensive state model with nested Pydantic models:
- `TaskRequirements`: Structured requirements from task parsing
- `CodebaseAnalysis`: Codebase analysis results
- `DependencyMapping`: Dependency and execution order mapping
- `ImplementationPlan`: Final implementation plan output

### Workflow Nodes
- **initialize**: Setup initial state and validate input
- **parse_task**: Extract requirements, acceptance criteria, constraints
- **analyze_codebase**: Analyze existing code, dependencies, affected files
- **map_dependencies**: Map execution order, dependencies, blocking steps
- **generate_plan**: Create detailed implementation plan (simple vs complex)
- **validate_plan**: Validate plan quality with retry mechanism (max 3 iterations)
- **finalize**: Prepare final output for implementor

### Tools
- **code_search_tool**: Search for code patterns in codebase
- **ast_parser_tool**: Parse Python files using AST for structure analysis
- **file_analyzer_tool**: Analyze files to determine changes needed
- **dependency_analyzer_tool**: Analyze dependencies and relationships
- **execution_order_tool**: Create execution order based on dependencies
- **task_parser_tool**: Parse task descriptions to extract requirements
- **effort_estimation_tool**: Estimate effort using complexity factors
- **risk_assessment_tool**: Assess risks and generate mitigation strategies

## Usage

### Basic Usage

```python
from agents.developer.planner import PlannerAgent

# Create planner agent
planner = PlannerAgent(
    model="gpt-4o",
    session_id="session_001",
    user_id="user_123"
)

# Run planning workflow
result = planner.run(
    task_description="Implement user authentication with email verification",
    codebase_context="Existing FastAPI app with PostgreSQL database",
    codebase_path="",  # Optional: path to codebase for analysis (empty = use default)
    thread_id="thread_001"
)

# Check results
if result["success"]:
    print(f"Task ID: {result['task_id']}")
    print(f"Complexity: {result['complexity_score']}/10")
    print(f"Estimated: {result['estimated_hours']} hours")
    print(f"Ready: {result['ready_for_implementation']}")
    
    # Access final plan
    final_plan = result["final_plan"]
    implementation_steps = final_plan["implementation"]["steps"]
```

### Using Custom Codebase Path

```python
# Analyze a specific codebase directory
result = planner.run(
    task_description="Add new feature to existing project",
    codebase_context="FastAPI backend with React frontend",
    codebase_path=r"D:\projects\my-app\backend",  # Specific path for analysis
    thread_id="thread_002"
)

# If codebase_path is empty or not provided, uses default path
result = planner.run(
    task_description="Add new feature",
    codebase_context="Existing codebase",
    # codebase_path defaults to: D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo
)
```

### Using Daytona Sandbox with GitHub Repository (NEW!)

```python
# Analyze GitHub repository using Daytona sandbox
result = planner.run(
    task_description="Implement user authentication with JWT tokens",
    codebase_context="FastAPI application with PostgreSQL database",
    github_repo_url="https://github.com/your-org/your-repo.git",  # GitHub repository
    thread_id="thread_003"
)

# For private repositories, ensure GitHub credentials are configured
result = planner.run(
    task_description="Add new feature to private repository",
    codebase_context="Private company codebase",
    github_repo_url="https://github.com/private-org/private-repo.git",
    thread_id="thread_004"
)

# Check if sandbox was used
if result.get("sandbox_id"):
    print(f"Used Daytona sandbox: {result['sandbox_id']}")
    print(f"Repository cloned to: {result.get('codebase_path', 'N/A')}")
else:
    print("Used local codebase analysis")
```

### Fallback Behavior

The planner supports multiple modes with automatic fallback:

1. **Daytona Sandbox Mode**: If `github_repo_url` is provided and Daytona is configured
2. **Local Path Mode**: If `codebase_path` is provided
3. **Default Mode**: Falls back to default local path

```python
# Priority order:
# 1. Daytona sandbox (if github_repo_url provided and Daytona available)
# 2. Custom local path (if codebase_path provided)
# 3. Default local path (fallback)

result = planner.run(
    task_description="Implement feature",
    github_repo_url="https://github.com/user/repo.git",  # Highest priority
    codebase_path="/custom/local/path",  # Ignored if sandbox succeeds
    # Falls back to default if both fail
)
```

### Integration with Implementor

```python
# Planner output becomes implementor input
planner_result = planner.run(
    task_description=task_description,
    codebase_context=codebase_context,
    codebase_path=r"D:\path\to\codebase"  # Optional custom path
)

if planner_result["ready_for_implementation"]:
    # Hand off to implementor
    implementor_result = implementor.run(
        implementation_plan=planner_result["final_plan"],
        thread_id=planner_result["metadata"]["thread_id"]
    )
```

## Configuration

### Environment Variables
```bash
# Required for LLM
OPENAI_API_KEY=your_openai_key

# Required for Langfuse tracing
LANGFUSE_SECRET_KEY=your_langfuse_secret
LANGFUSE_PUBLIC_KEY=your_langfuse_public
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional: Daytona Sandbox Configuration (for GitHub repository analysis)
DAYTONA_API_KEY=your_daytona_api_key
DAYTONA_API_URL=https://app.daytona.io/api
DAYTONA_TARGET=us

# Optional: GitHub Authentication (for private repositories)
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_personal_access_token
```

### Model Configuration
- Default model: `gpt-4o`
- Temperature: `0.3` (for consistent planning)
- Max tokens: Determined by model limits
- Timeout: 60 seconds per node

## Validation and Quality

### Validation Loop
- Plan validation with scoring (0.0-1.0)
- Automatic retry if score < 0.7
- Maximum 3 iterations per task
- Force finalization if max iterations reached

### Quality Metrics
- **Completeness**: All requirements addressed
- **Consistency**: Logical step ordering and dependencies
- **Effort Estimates**: Realistic hours and story points
- **Risk Assessment**: Comprehensive risk identification

### Success Criteria
- Validation score ≥ 0.7
- All required fields populated
- No circular dependencies
- Reasonable effort estimates

## Testing

### Run Tests
```bash
cd services/ai-agent-service/app/agents/developer/planner
python test_planner.py
```

### Test Coverage
- Basic functionality test
- Simple task planning
- Complex task planning
- Error handling
- Validation loop testing

## Integration Points

### Input (from Product Backlog)
- Task description (string)
- Codebase context (optional string)
- Thread ID for checkpointing

### Output (to Implementor)
- Final implementation plan (structured dict)
- Task metadata (complexity, estimates)
- Ready for implementation flag
- Validation results

### Monitoring (Langfuse)
- Workflow execution tracing
- Node-level performance metrics
- Error tracking and debugging
- User session tracking

## Best Practices

### For Task Descriptions
- Include clear requirements and acceptance criteria
- Specify technical constraints and preferences
- Provide business context and user stories
- Include any existing code references

### For Codebase Context
- Describe existing architecture patterns
- Mention relevant existing components
- Include technology stack information
- Note any constraints or limitations

### For Integration
- Always check `ready_for_implementation` flag
- Handle validation failures gracefully
- Use thread IDs for workflow continuity
- Monitor execution through Langfuse

## Troubleshooting

### Common Issues
1. **Validation failures**: Check task description clarity
2. **Tool errors**: Verify file paths and permissions
3. **LLM timeouts**: Reduce task complexity or increase timeout
4. **Import errors**: Check Python path and dependencies

### Debug Mode
Set environment variable for detailed logging:
```bash
export PLANNER_DEBUG=true
```

### Logs Location
- Workflow logs: Console output with emoji indicators
- Langfuse traces: Available in Langfuse dashboard
- Error logs: Captured in state.error_message

## Future Enhancements

### Planned Features
- Integration with actual code analysis tools
- Support for multiple programming languages
- Advanced risk assessment algorithms
- Machine learning-based effort estimation
- Integration with project management tools

### Performance Optimizations
- Parallel tool execution
- Caching of codebase analysis results
- Incremental planning for related tasks
- Optimized prompt engineering
