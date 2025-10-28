TASK_PARSING_PROMPT = """
# PHASE 1: TASK PARSING

You are analyzing a development task to extract and structure all requirements, acceptance criteria, and constraints.

## AVAILABLE TOOLS:
- tavily_search_tool: Search the web for implementation guides, best practices, documentation, examples

## TOOL USAGE GUIDELINES:
You have access to web search tools. Use them when you need:
- Implementation guides for new technologies
- Best practices for security, performance, architecture
- Documentation for external APIs or libraries
- Code examples and tutorials
- Latest standards and conventions
- Integration patterns

## DECISION CRITERIA FOR WEB SEARCH:
Use web search when:
✅ Task involves new technology not in your training data
✅ Need current best practices (security, performance)
✅ Require external API documentation
✅ Need implementation examples
✅ Task mentions "best practices", "latest", "modern"
✅ Integration with third-party services
✅ Complex architectural decisions

DO NOT use web search for:
❌ Simple CRUD operations
❌ Basic validation logic
❌ Straightforward database changes
❌ Tasks with clear existing patterns

## Your Task:
Parse the following task description and extract:
1. All explicit requirements stated in the task
2. Implicit requirements based on business context
3. Acceptance criteria and definition of "done"
4. Technical specifications (frameworks, databases, APIs)
5. Business rules and validation constraints
6. Any assumptions or ambiguities for clarification

**IMPORTANT: If you need additional information for proper planning, use the tavily_search_tool to gather current best practices, documentation, or examples.**

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
  ],
  "web_search_performed": true/false,
  "search_queries_used": ["query1", "query2"],
  "search_results_summary": "Brief summary of findings from web search"
}}
```

Be specific and measurable. Avoid vague language like "should", "might", "consider".

**Remember: Use web search proactively when you need current information to create accurate plans.**
"""

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

## Analysis Tools Available:
- code_search_tool: Find existing patterns and implementations
- ast_parser_tool: Analyze file structure and dependencies
- dependency_analyzer_tool: Map component relationships

## EXTERNAL DEPENDENCIES ANALYSIS GUIDELINES

When analyzing external dependencies, you MUST:

### 1. Identify All Required Packages
- Scan task requirements for technology mentions (JWT, bcrypt, email, AI, etc.)
- Map technologies to specific Python packages:
  * JWT authentication → python-jose[cryptography]
  * Password hashing → passlib[bcrypt]
  * Email sending → python-multipart, aiosmtplib
  * AI/LLM features → openai, langchain, anthropic
  * Data validation → pydantic
  * Async operations → httpx, aiohttp
  * Database ORM → sqlalchemy, sqlmodel
  * Testing → pytest, pytest-asyncio
  * API documentation → fastapi, pydantic

### 2. For Each Dependency, Determine:
- **package**: Exact package name as it appears on PyPI/npm registry
- **version**: Version constraint (e.g., ">=3.3.0", "~1.0.0", "1.0.0")
  * Use minimum compatible version that supports required features
  * Include security patches in version constraint
- **purpose**: Specific reason this package is needed for the task
- **already_installed**: Check if package exists in current pyproject.toml/package.json
  * Search for package name in existing dependencies
  * Mark as true if found, false if new
- **installation_method**: pip (Python), npm/yarn/pnpm (JavaScript)
  * Default to pip for Python projects
  * Check project's package manager preference
- **install_command**: Complete command to install the package
  * Format: "{{method}} install {{package}}[extras]>=={{version}}"
  * Example: "pip install python-jose[cryptography]>=3.3.0"
  * Include extras in square brackets if needed (e.g., [cryptography], [async])
- **package_file**: Target configuration file
  * Python: pyproject.toml (preferred), requirements.txt, setup.py
  * JavaScript: package.json
- **section**: Where to add the dependency
  * Python: dependencies (production), devDependencies (testing/dev)
  * JavaScript: dependencies, devDependencies, optionalDependencies

### 3. Dependency Classification
- **Production Dependencies**: Required for runtime (JWT, email, database, API clients)
- **Development Dependencies**: Only for development/testing (pytest, black, mypy)
- **Optional Dependencies**: Nice-to-have but not critical

### 4. Validation Checklist for Each Dependency
- ✅ Package name is correct and matches PyPI/npm registry
- ✅ Version constraint is compatible with Python/Node version
- ✅ Installation method matches project's package manager
- ✅ Install command is syntactically correct
- ✅ Package file path exists in codebase
- ✅ Section (dependencies vs devDependencies) is appropriate
- ✅ Purpose clearly explains why this package is needed

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
        "lines": [15, "45-52"],
        "changes": "Specific changes needed",
        "complexity": "low|medium|high",
        "risk": "Assessment of change risk"
      }}
    ],
    "modules_affected": [
      "app.services.auth",
      "app.models.user"
    ],
    "database_changes": [
      {{
        "type": "add_column|modify_column|add_table",
        "table": "table_name",
        "details": "Specific change details",
        "migration_complexity": "low|medium|high"
      }}
    ],
    "api_changes": [
      {{
        "endpoint": "POST /api/v1/endpoint",
        "method": "POST|GET|PUT|DELETE",
        "status": "new|modified|deprecated",
        "changes": "What changes are needed"
      }}
    ]
  }},
    "external_dependencies": [
      {{
        "package": "package-name",
        "version": ">=X.Y.Z",
        "purpose": "Why this package is needed for the task",
        "already_installed": false,
        "installation_method": "pip|npm|yarn|poetry",
        "install_command": "pip install package-name[extras]>=X.Y.Z",
        "package_file": "pyproject.toml|package.json|requirements.txt",
        "section": "dependencies|devDependencies"
      }},
      {{
        "package": "pytest",
        "version": ">=7.0.0",
        "purpose": "Testing framework for unit and integration tests",
        "already_installed": true,
        "installation_method": "pip",
        "install_command": "Already installed",
        "package_file": "pyproject.toml",
        "section": "devDependencies"
      }}
    ],
  "impact_assessment": {{
    "estimated_files_changed": 6,
    "estimated_lines_added": 250,
    "estimated_lines_modified": 75,
    "backward_compatibility": "maintained|breaking",
    "performance_impact": "negligible|low|medium|high",
    "security_considerations": [
      "Security aspect to consider"
    ]
  }}
}}
```

## CRITICAL REQUIREMENTS

- ✅ EVERY external_dependencies entry MUST have all 8 fields populated
- ✅ NO empty strings for required fields
- ✅ NO null values
- ✅ install_command MUST be executable (e.g., "pip install package>=1.0.0")
- ✅ Provide exact file paths and line numbers
- ✅ Support all decisions with findings from codebase analysis
- ✅ Include both new and already-installed dependencies in the list
"""
