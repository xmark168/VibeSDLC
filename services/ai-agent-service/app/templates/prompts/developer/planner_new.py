"""
Planner Agent Prompts - Simplified and Refactored

Contains all prompt templates for the 6-node Planner Agent workflow:
1. initialize
2. parse_task (with autonomous tool usage)
3. analyze_codebase
4. generate_plan (Chain of Vibe)
5. validate_plan
6. finalize
"""

# =============================================================================
# TASK PARSING PROMPT (Node: parse_task)
# =============================================================================

TASK_PARSING_PROMPT = """
# PHASE 1: TASK PARSING

You are an autonomous AI agent analyzing a development task to extract and structure all requirements, acceptance criteria, and constraints.

## Your Capabilities:
You have access to web search tools if you need additional information about:
- Technical specifications or best practices
- Framework/library documentation
- Industry standards or patterns
- Clarification of ambiguous requirements

**You decide autonomously** whether to use these tools based on:
- Clarity of the task description
- Completeness of the context provided
- Your confidence in understanding the requirements

## Your Task:
Parse the following task description and extract:
1. All explicit requirements stated in the task
2. Implicit requirements based on business context
3. Acceptance criteria and definition of "done"
4. Technical specifications (frameworks, databases, APIs)
5. Business rules and validation constraints
6. Any assumptions or ambiguities for clarification

## Task Description:
{task_description}

## Context Information:
{context}

## Output Format:
Return a JSON object with the following structure:
```json
{{
  "task_id": "Generated task ID",
  "task_title": "Clear, descriptive title",
  "functional_requirements": [
    "Explicit requirement 1 with specific details",
    "Explicit requirement 2 with acceptance threshold"
  ],
  "acceptance_criteria": [
    "Given [context] when [action] then [expected result]"
  ],
  "business_rules": {{
    "rule_name": "Detailed description and validation logic"
  }},
  "technical_specs": {{
    "framework": "Technology stack details",
    "database": "Database requirements",
    "apis": ["External API requirements"]
  }},
  "assumptions": [
    "Assumption requiring confirmation"
  ],
  "clarifications_needed": [
    "Question for Product Owner"
  ]
}}
```

Be specific and measurable. Avoid vague language like "should", "might", "consider".
"""


# =============================================================================
# CODEBASE ANALYSIS PROMPT (Node: analyze_codebase)
# =============================================================================

CODEBASE_ANALYSIS_PROMPT = """
# PHASE 2: CODEBASE ANALYSIS

You are analyzing the existing codebase to understand what files, modules, and components need to be created or modified for the given task.

## CRITICAL FILE PATH REQUIREMENTS:
- ALWAYS match file extensions to the detected tech stack
- Node.js/Express projects: Use .js files (NOT .py files)
- Python/FastAPI projects: Use .py files
- React/Next.js projects: Use .js/.jsx/.ts/.tsx files
- Database migrations: Match the tech stack's migration format
  * Node.js: Use Sequelize/Knex/Prisma migration files (.js)
  * Python: Use Alembic migration files (.py)
- NEVER generate .py files for Node.js projects
- NEVER generate .js files for Python projects

## Your Task:
Analyze the codebase and identify:
1. All files requiring modification (provide exact paths with CORRECT extensions)
2. New files to be created (with CORRECT extensions for the tech stack)
3. Affected modules and their interdependencies
4. Database schema changes required (with correct migration format)
5. API endpoints to be created, modified, or deprecated
6. Testing requirements and existing test infrastructure
7. External packages/dependencies required for implementation
8. Package manager and installation commands for new dependencies

## Task Requirements:
{task_requirements}

## Tech Stack:
{tech_stack}

## Codebase Context:
{codebase_context}

## EXTERNAL DEPENDENCIES ANALYSIS GUIDELINES

When analyzing external dependencies, you MUST:

### 1. Identify All Required Packages
For each new package needed:
- Specify exact package name
- Recommend specific version or version range
- Explain why this package is needed
- Identify if package is already installed in the project

### 2. Determine Installation Method
Based on tech stack, specify:
- **Python projects**: pip, poetry, or conda
- **Node.js projects**: npm, yarn, or pnpm
- **Ruby projects**: gem or bundler
- **Go projects**: go get or go mod

### 3. Provide Installation Commands
Generate exact commands for package manager:
```bash
# Python with pip
pip install package-name>=X.Y.Z

# Python with poetry
poetry add package-name@^X.Y.Z

# Node.js with npm
npm install package-name@^X.Y.Z

# Node.js with yarn
yarn add package-name@^X.Y.Z
```

### 4. Specify Package File Updates
Identify which file needs to be updated:
- Python: `requirements.txt`, `pyproject.toml`, `setup.py`
- Node.js: `package.json`
- Ruby: `Gemfile`
- Go: `go.mod`

### 5. Categorize Dependencies
Specify dependency type:
- **Production dependencies**: Required for runtime
- **Development dependencies**: Required only for development/testing

## Output Format:
Return a JSON object with the following structure:
```json
{{
  "codebase_analysis": {{
    "files_to_create": [
      {{
        "path": "exact/file/path.ext",
        "reason": "Why this file is needed",
        "template": "Reference pattern to follow"
      }}
    ],
    "files_to_modify": [
      {{
        "path": "exact/file/path.ext",
        "changes": "Specific changes needed",
        "complexity": "low|medium|high"
      }}
    ],
    "database_changes": [
      {{
        "type": "add_table|add_column|modify_column",
        "table": "table_name",
        "details": "Specific change details"
      }}
    ],
    "external_dependencies": [
      {{
        "package": "package-name",
        "version": ">=X.Y.Z",
        "purpose": "Why this package is needed",
        "already_installed": false,
        "installation_method": "pip|npm|yarn|poetry",
        "install_command": "pip install package-name>=X.Y.Z",
        "package_file": "requirements.txt|package.json",
        "dependency_type": "production|development"
      }}
    ],
    "internal_dependencies": [
      {{
        "module": "app.core.security",
        "components": ["hash_password", "verify_password"],
        "status": "exists|needs_creation"
      }}
    ]
  }}
}}
```

Be thorough and precise. Verify all file paths and extensions match the tech stack.
"""


# =============================================================================
# PLAN GENERATION PROMPT (Node: generate_plan)
# =============================================================================

GENERATE_PLAN_PROMPT = """
# PHASE 3: PLAN GENERATION (Chain of Vibe Methodology)

You are creating a detailed implementation plan using the "Chain of Vibe" methodology for hierarchical, incremental task decomposition.

## Task Context:
{task_context}

## Codebase Analysis:
{codebase_analysis}

## Chain of Vibe Principles:
1. **Hierarchical Breakdown**: Each major step decomposes into atomic sub-steps
2. **Logical Dependencies**: Steps ordered by technical dependencies (data → logic → UI)
3. **Actionable Granularity**: Each sub-step is a single, testable change
4. **Incremental Execution**: Each sub-step produces working code that can be committed
5. **Full-Stack Coverage**: Unified plan covering backend → frontend → integration

## Output Format:
Generate a detailed implementation plan in JSON format:

```json
{{
  "task_id": "TSK-XXXX",
  "description": "Clear description of what will be implemented",
  "complexity_score": 1-10,
  "plan_type": "simple|complex",
  
  "functional_requirements": [
    "Requirement 1 extracted from task",
    "Requirement 2 extracted from task"
  ],
  
  "steps": [
    {{
      "step": 1,
      "title": "Step title",
      "description": "Detailed description of what to do",
      "category": "backend|frontend|database|testing|integration",
      "sub_steps": [
        {{
          "sub_step": "1.1",
          "title": "Sub-step title",
          "description": "Detailed description"
        }},
        {{
          "sub_step": "1.2",
          "title": "Sub-step title",
          "description": "Detailed description"
        }}
      ]
    }}
  ],
  
  "database_changes": [
    {{
      "change": "Add users table",
      "fields": ["id", "email", "password_hash", "created_at"],
      "affected_step": 1
    }}
  ],
  
  "external_dependencies": [
    {{
      "package": "package-name",
      "version": "^X.Y.Z",
      "purpose": "Why this package is needed"
    }}
  ],
  
  "internal_dependencies": [
    {{
      "module": "Module name",
      "required_by_step": 2
    }}
  ],
  
  "story_points": 5,
  
  "execution_order": [
    "Execute steps sequentially: 1 → 2 → 3 → 4",
    "Within each step, execute sub-steps in order",
    "Test after each sub-step before proceeding",
    "Commit code after each completed sub-step"
  ]
}}
```

## CRITICAL JSON SCHEMA RULES:
1. **Steps**: Each step MUST have: step (number), title, description, category, sub_steps (array)
2. **Sub-steps**: Each sub-step MUST have ONLY 3 fields:
   - "sub_step": "X.Y" (string format)
   - "title": "Brief action title"
   - "description": "Detailed description"
3. **Categories**: Use "backend", "frontend", "database", "testing", or "integration"
4. **Story Points**: Use Fibonacci sequence (1, 2, 3, 5, 8, 13, 21)

## STRICT OUTPUT RULES:
- Output ONLY valid JSON, no markdown code blocks
- Follow the EXACT schema shown above
- Do NOT add extra fields to sub-steps (only sub_step, title, description)
- Do NOT add file_changes, estimated_time, or any other fields
- Ensure all JSON is properly formatted and parseable
"""

