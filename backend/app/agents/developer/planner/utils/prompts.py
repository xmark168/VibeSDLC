"""
Planner Agent Prompts

Contains all prompt templates for the Planner Agent.
"""

import json

# ============================================================================
# TASK PARSING PROMPT - Phase 1: Task Parsing
# ============================================================================

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


# ============================================================================
# CODEBASE ANALYSIS PROMPT - Phase 2: Codebase Analysis
# ============================================================================

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

## Existing Dependencies (from package.json/pyproject.toml):
{existing_dependencies}

## Previously Suggested Dependencies (from earlier tasks in this session):
{previously_suggested_dependencies}

## Analysis Tools Available:
- code_search_tool: Find existing patterns and implementations
- ast_parser_tool: Analyze file structure and dependencies
- dependency_analyzer_tool: Map component relationships

## EXTERNAL DEPENDENCIES ANALYSIS GUIDELINES

When analyzing external dependencies, you MUST follow this process:

### 1. Check Existing Dependencies FIRST
- Review the "Existing Dependencies" section above (from package.json/pyproject.toml)
- If a package is already listed in dependencies or devDependencies, mark it as already_installed: true
- DO NOT include packages that are already installed in the external_dependencies list for this task

### 2. Check Previously Suggested Dependencies SECOND
- Review the "Previously Suggested Dependencies" section above (from earlier tasks)
- These packages were suggested in previous tasks in this planning session
- DO NOT include these packages in the current task's external_dependencies list
- They will be installed when their respective tasks are executed

### 3. Filter Out Built-in Modules
- Node.js built-in modules: crypto, fs, path, http, https, util, events, stream, buffer, etc.
- Python built-in modules: os, sys, json, datetime, re, collections, etc.
- DO NOT include built-in modules in external_dependencies

### 4. Identify NEW Required Packages Only
After checking existing and previously suggested dependencies, identify ONLY NEW packages needed:
- Scan task requirements for technology mentions (JWT, bcrypt, email, AI, etc.)
- Map technologies to specific packages:
  * Node.js examples:
    - JWT authentication → jsonwebtoken
    - Password hashing → bcryptjs or bcrypt
    - Email sending → nodemailer
    - Rate limiting → express-rate-limit
    - Validation → joi or yup
    - Testing → jest, mocha, chai
  * Python examples:
    - JWT authentication → python-jose[cryptography]
    - Password hashing → passlib[bcrypt]
    - Email sending → python-multipart, aiosmtplib
    - AI/LLM features → openai, langchain, anthropic
    - Data validation → pydantic
    - Async operations → httpx, aiohttp
    - Database ORM → sqlalchemy, sqlmodel
    - Testing → pytest, pytest-asyncio

### 5. For Each NEW Dependency, Determine:
- **package**: Exact package name as it appears on PyPI/npm registry
- **version**: Version constraint (e.g., ">=3.3.0", "~1.0.0", "1.0.0")
  * Use minimum compatible version that supports required features
  * Include security patches in version constraint
- **purpose**: Specific reason this package is needed for THIS SPECIFIC TASK
- **already_installed**: MUST be false (since we already filtered out installed packages)
- **installation_method**: pip (Python), npm/yarn/pnpm (JavaScript)
  * Default to pip for Python projects
  * Check project's package manager preference (look for yarn.lock, pnpm-lock.yaml)
- **install_command**: Complete command to install the package
  * Format: "{{method}} install {{package}}[extras]>=={{version}}"
  * Example: "pip install python-jose[cryptography]>=3.3.0"
  * Example: "npm install express-rate-limit@^5.3.0"
  * Include extras in square brackets if needed (e.g., [cryptography], [async])
- **package_file**: Target configuration file
  * Python: pyproject.toml (preferred), requirements.txt, setup.py
  * JavaScript: package.json
- **section**: Where to add the dependency
  * Python: dependencies (production), devDependencies (testing/dev)
  * JavaScript: dependencies, devDependencies, optionalDependencies

### 6. Dependency Classification
- **Production Dependencies**: Required for runtime (JWT, email, database, API clients)
- **Development Dependencies**: Only for development/testing (pytest, black, mypy, jest)
- **Optional Dependencies**: Nice-to-have but not critical

### 7. Validation Checklist for Each Dependency
- ✅ Package name is correct and matches PyPI/npm registry
- ✅ Package is NOT in "Existing Dependencies" section
- ✅ Package is NOT in "Previously Suggested Dependencies" section
- ✅ Package is NOT a built-in module (crypto, fs, os, sys, etc.)
- ✅ Version constraint is compatible with Python/Node version
- ✅ Installation method matches project's package manager
- ✅ Install command is syntactically correct
- ✅ Package file path exists in codebase

## CRITICAL RULES FOR EXTERNAL DEPENDENCIES

1. **ONLY include NEW packages** that are:
   - ✅ NOT in existing_dependencies (already installed)
   - ✅ NOT in previously_suggested_dependencies (suggested in earlier tasks)
   - ✅ NOT built-in modules
   - ✅ Actually needed for THIS SPECIFIC TASK

2. **If NO new packages are needed**, return empty array: `"external_dependencies": []`

3. **Example scenarios**:
   - TASK-001 needs: bcryptjs, jsonwebtoken, joi → Include all 3
   - TASK-002 needs: jsonwebtoken (already in TASK-001), express-rate-limit → Include ONLY express-rate-limit
   - TASK-003 needs: jsonwebtoken (already in TASK-001), bcryptjs (already in TASK-001) → Include NOTHING: []
   - TASK-004 needs: crypto (built-in) → Include NOTHING: []
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
        "package": "express-rate-limit",
        "version": "^5.3.0",
        "purpose": "Rate limiting middleware to prevent brute force attacks on login endpoint",
        "already_installed": false,
        "installation_method": "npm",
        "install_command": "npm install express-rate-limit@^5.3.0",
        "package_file": "package.json",
        "section": "dependencies"
      }}
    ],
    "note": "Only include NEW packages not in existing_dependencies or previously_suggested_dependencies. If no new packages needed, use empty array: []"
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
- ✅ install_command MUST be executable (e.g., "npm install package@^1.0.0")
- ✅ Provide exact file paths and line numbers
- ✅ Support all decisions with findings from codebase analysis
- ✅ ONLY include NEW packages not in existing_dependencies or previously_suggested_dependencies
- ✅ DO NOT include built-in modules (crypto, fs, path, os, sys, etc.)
- ✅ If no new packages needed, use empty array: "external_dependencies": []
"""


def _get_backend_guidelines() -> str:
    """Get backend planning guidelines section."""
    return """## BACKEND PLANNING GUIDELINES (Node.js + Express)

When planning backend implementation, you MUST include ALL necessary steps for a production-ready feature following **layered architecture** principles:

### MANDATORY BACKEND STEPS CHECKLIST:

**1. Database Schema and Models** - Migrations, ORM/ODM models, relationships, validations (e.g., `be/src/models/User.js`)
**2. Data Access Layer / Repositories** - CRUD operations, complex queries, transactions (e.g., `be/src/repositories/UserRepository.js`)
**3. Service Layer** - Business logic, validation, transformation, error handling (e.g., `be/src/services/AuthService.js`)
**4. Input Validation** - Validation schemas for request bodies/params using Joi/Zod (e.g., `be/src/validators/authValidator.js`)
**5. Controller Layer** - Request/response handling, delegates to services (e.g., `be/src/controllers/AuthController.js`)
**6. Route Definitions** - RESTful API routes with middleware (e.g., `be/src/routes/auth.js`)
**7. Authentication Middleware** - JWT generation/verification, token refresh (e.g., `be/src/middleware/auth.js`)
**8. Authorization Middleware** - Permission checking, role verification (e.g., `be/src/middleware/authorize.js`)
**9. Error Handling Middleware** - Global error handler, custom error classes (e.g., `be/src/middleware/errorHandler.js`)
**10. Request Logging** - Winston/Morgan setup, structured logging (e.g., `be/src/middleware/logger.js`)
**11. Environment Configuration** - .env setup, config validation (e.g., `be/src/config/index.js`)
**12. Database Connection** - Connection pooling, migrations, seeding (e.g., `be/src/config/database.js`)
**13. API Documentation** - Swagger/OpenAPI docs (e.g., `be/swagger.yaml`)
**14. Unit Tests** - Jest/Mocha tests for services/repositories (e.g., `be/tests/unit/services/AuthService.test.js`)
**15. Integration Tests** - API endpoint tests with Supertest (e.g., `be/tests/integration/auth.test.js`)
**16. Dependency Installation** - Add required npm packages to package.json
**17. Main Application Setup** - Update app.js with routes and middleware (e.g., `be/src/app.js`)

### BACKEND STEP ORDERING:

**Recommended Order:** Models → Repositories → Validation → Services → Controllers → Routes → Middleware → Testing → Documentation

### LAYERED ARCHITECTURE PRINCIPLES:

**Layer Flow (Bottom-Up):**
```
Database Layer (MongoDB)
    ↓
Models Layer (ORM/ODM models)
    ↓
Repository Layer (Data Access)
    ↓
Service Layer (Business Logic)
    ↓
Controller Layer (Request Handling)
    ↓
Route Layer (API Endpoints)
    ↓
Middleware Layer (Auth, Validation, Error Handling)
    ↓
Application Layer (Express App)
```

**Dependency Rules:**
- Routes depend on Controllers
- Controllers depend on Services
- Services depend on Repositories
- Repositories depend on Models
- Models depend on Database
- Each layer should only depend on the layer directly below it
- No circular dependencies

### COMMON MISTAKES:

❌ **DON'T**: Mix business logic in controllers, skip Repository/Service layers, forget validation/error handling/tests
✅ **DO**: Follow layered architecture, keep controllers thin, validate inputs, add comprehensive tests
"""


def _get_frontend_guidelines() -> str:
    """Get frontend planning guidelines section."""
    return """## FRONTEND PLANNING GUIDELINES (React + TypeScript + Vite)

When planning frontend implementation, you MUST include ALL necessary steps for a production-ready feature:

### MANDATORY FRONTEND STEPS CHECKLIST:

**1. TypeScript Types** - Interfaces for data structures, API types, component props (e.g., `fe/src/types/auth.ts`)
**2. API Client Config** - Axios/Fetch setup, interceptors, token injection (e.g., `fe/src/api/client.ts`)
**3. API Service Layer** - Service functions for endpoints (e.g., `fe/src/services/authService.ts`)
**4. Custom Hooks** - Feature-specific hooks for state/logic (e.g., `fe/src/hooks/useAuth.ts`)
**5. Form Validation** - Zod/Yup schemas, error messages (e.g., `fe/src/validation/authSchema.ts`)
**6. Reusable UI Components** - Button, Input, Card components (e.g., `fe/src/components/ui/Button.tsx`)
**7. Feature Components** - Core feature components with state (e.g., `fe/src/components/auth/LoginForm.tsx`)
**8. Layout Components** - Page layouts, navigation (e.g., `fe/src/layouts/AuthLayout.tsx`)
**9. Routing Setup** - React Router routes, navigation (e.g., update `fe/src/App.tsx`)
**10. Protected Routes** - Authentication guards (e.g., `fe/src/components/ProtectedRoute.tsx`)
**11. Global State** - Context/Redux/Zustand for shared state (e.g., `fe/src/context/AuthContext.tsx`)
**12. Error Handling** - Error boundaries, toast notifications (e.g., `fe/src/components/ErrorBoundary.tsx`)
**13. Loading States** - Spinners, skeleton screens (e.g., `fe/src/components/ui/Spinner.tsx`)
**14. Token Management** - Token storage, refresh, expiration (e.g., `fe/src/utils/tokenManager.ts`)

### FRONTEND STEP ORDERING:

**Recommended Order:** Types → API Config → UI Components → Validation → Services → Hooks → Layouts → Feature Components → Routing → Guards → Error Handling → Loading → Integration

### COMMON MISTAKES:

❌ **DON'T**: Skip types/validation/API config, create only forms without infrastructure, forget error handling/loading states
✅ **DO**: Include ALL infrastructure steps, create types before components, add error handling and loading states
"""


def create_chain_of_vibe_prompt(
    state,
    task_requirements,
    detailed_codebase_context: str,
    project_structure: dict,
    architecture_guidelines_text: str,
    task_scope: str = "",
    existing_dependencies: str = "",
) -> str:
    """
    Create Chain of Vibe implementation planning prompt.

    Args:
        state: PlannerState with tech_stack
        task_requirements: TaskRequirements object
        detailed_codebase_context: Detailed context string
        project_structure: Project structure dict
        architecture_guidelines_text: Architecture guidelines text
        task_scope: Task scope from labels (backend, frontend, full-stack)
        existing_dependencies: Formatted string of existing dependencies from package.json/requirements.txt

    Returns:
        Formatted prompt string
    """

    prompt = f"""# CHAIN OF VIBE IMPLEMENTATION PLANNING

You are an expert implementation planner using the "Chain of Vibe" methodology for hierarchical, incremental task decomposition.

## TASK CONTEXT

Tech Stack: {state.tech_stack or "unknown"}
Task ID: {task_requirements.task_id}
Task Title: {task_requirements.task_title}

Requirements:
{json.dumps(task_requirements.requirements, indent=2)}

Acceptance Criteria:
{json.dumps(task_requirements.acceptance_criteria, indent=2)}

Technical Specs:
{json.dumps(task_requirements.technical_specs, indent=2)}


## DETAILED CODEBASE CONTEXT

{detailed_codebase_context}


Existing Project Structure:
{json.dumps(project_structure, indent=2)}

## EXISTING DEPENDENCIES

{existing_dependencies if existing_dependencies else "No existing dependencies found in package.json/requirements.txt"}

{architecture_guidelines_text}

## OUTPUT FORMAT

Generate a detailed implementation plan in JSON format:

```json
{{
  "task_id": "{task_requirements.task_id}",
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
      "title": "Create User Model",
      "description": "Define User model with Mongoose schema",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "1.1",
          "title": "Define User schema with email, password_hash, is_verified, created_at, updated_at fields"
        }},
        {{
          "sub_step": "1.2",
          "title": "Add unique index on email field and timestamps"
        }},
        {{
          "sub_step": "1.3",
          "title": "Add pre-save hook for password hashing using bcrypt"
        }}
      ]
    }},
    {{
      "step": 2,
      "title": "Create User Repository",
      "description": "Implement data access layer",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "2.1",
          "title": "Create UserRepository class with findByEmail() method"
        }},
        {{
          "sub_step": "2.2",
          "title": "Implement create() method with duplicate email handling"
        }},
        {{
          "sub_step": "2.3",
          "title": "Add updateVerificationStatus() and findById() methods"
        }}
      ]
    }},
    {{
      "step": 3,
      "title": "Create Input Validation Schemas",
      "description": "Define validation schemas using Joi",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "3.1",
          "title": "Create registerSchema with email, password validation rules"
        }},
        {{
          "sub_step": "3.2",
          "title": "Create loginSchema with email and password validation"
        }}
      ]
    }},
    {{
      "step": 4,
      "title": "Implement Auth Service",
      "description": "Create business logic layer",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "4.1",
          "title": "Create AuthService class with registerUser() method including duplicate check"
        }},
        {{
          "sub_step": "4.2",
          "title": "Implement loginUser() with password verification and JWT generation"
        }},
        {{
          "sub_step": "4.3",
          "title": "Add sendVerificationEmail() method with token generation"
        }}
      ]
    }},
    {{
      "step": 5,
      "title": "Create Auth Controller",
      "description": "Implement thin controller layer",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "5.1",
          "title": "Create AuthController with register() handler delegating to AuthService"
        }},
        {{
          "sub_step": "5.2",
          "title": "Implement login() handler with error handling and response formatting"
        }}
      ]
    }},
    {{
      "step": 6,
      "title": "Define Authentication Routes",
      "description": "Setup API endpoints",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "6.1",
          "title": "Create auth router with POST /api/auth/register route and validation middleware"
        }},
        {{
          "sub_step": "6.2",
          "title": "Add POST /api/auth/login route with rate limiting"
        }}
      ]
    }},
    {{
      "step": 7,
      "title": "Create TypeScript Types",
      "description": "Define frontend types",
      "category": "frontend",
      "sub_steps": [
        {{
          "sub_step": "7.1",
          "title": "Create User interface with id, email, isVerified properties"
        }},
        {{
          "sub_step": "7.2",
          "title": "Define LoginRequest, RegisterRequest, and AuthResponse types"
        }}
      ]
    }},
    {{
      "step": 8,
      "title": "Create Auth API Service",
      "description": "Implement frontend API client",
      "category": "frontend",
      "sub_steps": [
        {{
          "sub_step": "8.1",
          "title": "Setup axios instance with base URL and interceptors"
        }},
        {{
          "sub_step": "8.2",
          "title": "Create AuthService with login() and register() methods"
        }},
        {{
          "sub_step": "8.3",
          "title": "Add error handling and token storage logic"
        }}
      ]
    }},
    {{
      "step": 9,
      "title": "Create Login Form Component",
      "description": "Build React login form",
      "category": "frontend",
      "sub_steps": [
        {{
          "sub_step": "9.1",
          "title": "Create LoginForm component with react-hook-form setup"
        }},
        {{
          "sub_step": "9.2",
          "title": "Add form validation rules and error message display"
        }},
        {{
          "sub_step": "9.3",
          "title": "Implement submit handler with loading state and error handling"
        }}
      ]
    }},
    {{
      "step": 10,
      "title": "Setup Frontend Routing and Protected Routes",
      "description": "Configure React Router and authentication guards",
      "category": "frontend",
      "sub_steps": [
        {{
          "sub_step": "10.1",
          "title": "Add /login and /register routes to App.tsx"
        }},
        {{
          "sub_step": "10.2",
          "title": "Create ProtectedRoute component with authentication check"
        }},
        {{
          "sub_step": "10.3",
          "title": "Add navigation links and route guards"
        }}
      ]
    }},
    {{
      "step": 11,
      "title": "Write Backend Tests",
      "description": "Create unit and integration tests for backend",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "11.1",
          "title": "Write unit tests for AuthService.registerUser() and loginUser()"
        }},
        {{
          "sub_step": "11.2",
          "title": "Write unit tests for UserRepository methods"
        }},
        {{
          "sub_step": "11.3",
          "title": "Write integration tests for POST /api/auth/login and /register endpoints"
        }}
      ]
    }}
  ],

  "database_changes": [
    {{"change": "Add users table", "fields": ["id", "email", "password_hash", "is_verified"], "affected_step": 1}}
  ],

  "external_dependencies": [
    {{
      "package": "mongoose",
      "version": "^8.0.0",
      "purpose": "MongoDB ODM for user data storage",
      "category": "backend",
      "already_installed": false,
      "installation_method": "npm",
      "install_command": "cd be && npm install mongoose@^8.0.0",
      "package_file": "be/package.json",
      "dependency_type": "production"
    }},
    {{
      "package": "bcrypt",
      "version": "^5.1.0",
      "purpose": "Password hashing for security",
      "category": "backend",
      "already_installed": false,
      "installation_method": "npm",
      "install_command": "cd be && npm install bcrypt@^5.1.0",
      "package_file": "be/package.json",
      "dependency_type": "production"
    }},
    {{
      "package": "joi",
      "version": "^17.11.0",
      "purpose": "Input validation schemas",
      "category": "backend",
      "already_installed": false,
      "installation_method": "npm",
      "install_command": "cd be && npm install joi@^17.11.0",
      "package_file": "be/package.json",
      "dependency_type": "production"
    }},
    {{
      "package": "react-hook-form",
      "version": "^7.48.0",
      "purpose": "Form validation and state management",
      "category": "frontend",
      "already_installed": false,
      "installation_method": "npm",
      "install_command": "cd fe && npm install react-hook-form@^7.48.0",
      "package_file": "fe/package.json",
      "dependency_type": "production"
    }}
  ],

  "internal_dependencies": [
    {{"module": "User model", "required_by_step": 2}},
    {{"module": "UserRepository", "required_by_step": 4}},
    {{"module": "Auth types", "required_by_step": 8}}
  ],

  "story_points": 8,

  "execution_order": [
    "Backend (1-6, 11): Models → Repository → Validation → Service → Controller → Routes → Tests",
    "Frontend (7-10): Types → API Service → Components → Routing"
  ]
}}
```

## CRITICAL REQUIREMENTS

### Core Principles:
1. **Hierarchical Breakdown**: Each major step decomposes into atomic sub-steps
2. **Logical Dependencies**: Steps ordered by technical dependencies (data → logic → UI)
3. **Actionable Granularity**: Each sub-step is a single, testable change
4. **Incremental Execution**: Each sub-step produces working code that can be committed
5. **Full-Stack Coverage**: Unified plan covering backend → frontend

### JSON Schema Rules:
1. **Steps**: Each step MUST have: step (number), title, description, category, sub_steps (array)
2. **Sub-steps**: Each sub-step MUST have ONLY 3 fields:
   - "sub_step": "X.Y" (string format)
   - "title": "Brief action title"
   - "description": "Detailed description"
3. **Categories**: Use ONLY "backend" or "frontend" (database/testing steps should use "backend" or "frontend" category)
4. **Database Changes**: Include change, fields (array), affected_step
5. **Dependencies**:
   - external_dependencies: MUST have ALL 9 fields (package, version, purpose, category, already_installed, installation_method, install_command, package_file, dependency_type)
   - internal_dependencies: module, required_by_step
6. **Execution Order**: Array of strings describing sequential execution flow
7. **Story Points**: Use Fibonacci sequence (1, 2, 3, 5, 8, 13, 21)

## EXTERNAL DEPENDENCIES REQUIREMENTS

### CRITICAL RULES:
1. **Check Existing Dependencies FIRST**: Review the "EXISTING DEPENDENCIES" section above
2. **No Duplicates**: If a package is already in existing dependencies, set `already_installed: true`
3. **Complete Information**: Every external_dependencies entry MUST have ALL 9 fields:
   - `package`: Package name (string)
   - `version`: Version constraint (string, e.g., "^8.0.0", ">=3.3.0")
   - `purpose`: Detailed explanation of why this package is needed (string)
   - `category`: "backend" or "frontend" (string)
   - `already_installed`: true if package exists in existing dependencies, false otherwise (boolean)
   - `installation_method`: "npm" | "yarn" | "pip" | "poetry" (string)
   - `install_command`: Full executable command with directory navigation (string, e.g., "cd be && npm install express@^4.18.0")
   - `package_file`: Full path from root (string, e.g., "be/package.json", "fe/package.json", "backend/package.json")
   - `dependency_type`: "production" | "development" (string)

### CATEGORIZATION RULES:
- **Backend-only task** (`task_scope: "backend"`): All dependencies have `category: "backend"`
- **Frontend-only task** (`task_scope: "frontend"`): All dependencies have `category: "frontend"`
- **Full-stack task** (`task_scope: "full-stack"`): Categorize each package:
  - Backend: mongoose, express, bcrypt, joi, jsonwebtoken, nodemailer, etc.
  - Frontend: react, vue, axios, react-hook-form, zod, @types/*, etc.

### DIRECTORY STRUCTURE RULES:
- **Backend dependencies** (`category: "backend"`):
  - `package_file`: "be/package.json" or "backend/package.json"
  - `install_command`: "cd be && npm install ..." or "cd backend && npm install ..."
- **Frontend dependencies** (`category: "frontend"`):
  - `package_file`: "fe/package.json" or "frontend/package.json"
  - `install_command`: "cd fe && npm install ..." or "cd frontend && npm install ..."
- **Root-level dependencies** (monorepo or no category):
  - `package_file`: "package.json"
  - `install_command`: "npm install ..." (no cd command)

### VALIDATION CHECKLIST:
- ✅ Package is NOT in existing dependencies (unless marking as already_installed: true)
- ✅ Package name matches npm/PyPI registry
- ✅ Version constraint is valid (^X.Y.Z, >=X.Y.Z, ~X.Y.Z)
- ✅ Category matches task scope or is correctly classified for full-stack
- ✅ Installation method matches project type (npm for Node.js, pip for Python)
- ✅ Install command includes correct directory navigation (cd be/fe && ...)
- ✅ Package file path matches category (backend → be/, frontend → fe/)
- ✅ Install command directory matches package_file directory
- ✅ Dependency type is appropriate (production for runtime, development for testing/build)

### EXAMPLES:
- **Already installed**: `{{"package": "express", "already_installed": true, "install_command": "Already installed", ...}}`
- **New backend package**: `{{"package": "mongoose", "category": "backend", "install_command": "cd be && npm install mongoose@^8.0.0", "package_file": "be/package.json", ...}}`
- **New frontend package**: `{{"package": "react-hook-form", "category": "frontend", "install_command": "cd fe && npm install react-hook-form@^7.48.0", "package_file": "fe/package.json", ...}}`
- **Root-level package**: `{{"package": "lerna", "category": "backend", "install_command": "npm install lerna@^7.0.0", "package_file": "package.json", ...}}`
"""

    # Add scope-specific guidelines
    scope_guidelines = ""

    # Determine which guidelines to include based on task_scope
    if task_scope == "backend":
        # Backend-only task
        scope_guidelines = _get_backend_guidelines()
        expected_steps = "12-18 steps"
        scope_description = "Backend feature"
    elif task_scope == "frontend":
        # Frontend-only task
        scope_guidelines = _get_frontend_guidelines()
        expected_steps = "10-16 steps"
        scope_description = "Frontend feature"
    else:
        # Full-stack or unknown scope - include both
        scope_guidelines = (
            _get_backend_guidelines() + "\n\n" + _get_frontend_guidelines()
        )
        expected_steps = "18-25+ steps"
        scope_description = "Full-stack feature"

    prompt += f"""
{scope_guidelines}


**CRITICAL WARNING - READ CAREFULLY:**

🚨 **The example above is SIMPLIFIED for demonstration purposes ONLY!**

**What the example shows:**
- ✅ Correct JSON schema structure (steps, sub_steps, dependencies, execution_order)
- ✅ Proper layered architecture flow (Models → Repository → Service → Controller → Routes)
- ✅ Both backend AND frontend steps included

**What you MUST do differently:**
- ❌ DO NOT copy the example content or structure
- ❌ DO NOT limit yourself to 10 steps - generate {expected_steps} for this {scope_description}
- ❌ DO NOT use only 2-3 sub-steps per step - use 3-5 sub-steps for complex steps
- ✅ MUST generate MORE DETAILED plans based on the MANDATORY CHECKLISTS above
- ✅ MUST break down each step into ATOMIC, ACTIONABLE sub-steps

**For this {scope_description}, you should generate {expected_steps}**

## GENERATE PLAN NOW

Analyze the task requirements and generate a complete Chain of Vibe implementation plan.

**STRICT OUTPUT RULES:**
- Output ONLY valid JSON, no markdown code blocks
- Follow the EXACT JSON schema format shown in the example above
- Do NOT copy the example content - generate your own plan based on task requirements
- Do NOT add extra fields to sub-steps (only sub_step, title, description)
- Do NOT add file_changes, estimated_time, or any other fields
- Ensure all JSON is properly formatted and parseable
"""

    # Add scope-specific instructions
    if task_scope == "backend":
        prompt += """
**FOR THIS BACKEND FEATURE (Node.js + Express):**
- MANDATORY: Use the BACKEND PLANNING GUIDELINES checklist (17 mandatory steps)
- ALWAYS include these layers in order: Models → Repositories → Services → Controllers → Routes
- MUST include: Validation schemas, Error handling middleware, Logging, Environment config, Database connection, API docs, Unit tests, Integration tests
- Do NOT mix business logic into controllers (controllers should only handle HTTP request/response)
- Do NOT put database queries in controllers (use Repository layer)
- Do NOT skip Repository layer (required for data access operations)
- Do NOT skip Service layer (required for business logic)
- Each backend feature should have 12-18 steps (NOT 6-8 like the simplified example)
- Each step should have 2-5 atomic sub-steps (NOT just 1-2)
- Use category "backend" for all steps
"""
    elif task_scope == "frontend":
        prompt += """
**FOR THIS FRONTEND FEATURE (React + TypeScript + Vite):**
- MANDATORY: Use the FRONTEND PLANNING GUIDELINES checklist (15 mandatory categories)
- MUST include: Types, API Config, UI Components, Validation, Services, Hooks, Layouts, Feature Components, Pages, Routing, Guards, Context, Error Handling, Loading States, Token Management
- Do NOT skip infrastructure steps (types, API config, validation, error handling, etc.)
- Follow the recommended step ordering: Types → API Config → UI Components → Validation → Services → Hooks → Layouts → Feature Components → Pages → Routing → Guards → Context → Error Handling → Loading → Tokens → Integration
- Each frontend feature should have 10-16 steps (NOT 3-4 like the simplified example)
- Each step should have 2-4 atomic sub-steps (NOT just 1)
- Use category "frontend" for all steps
"""
    else:
        # Full-stack
        prompt += """
**FOR THIS FULL-STACK FEATURE:**

**BACKEND (Node.js + Express):**
- MANDATORY: Use the BACKEND PLANNING GUIDELINES checklist (17 mandatory steps)
- ALWAYS include these layers in order: Models → Repositories → Services → Controllers → Routes
- MUST include: Validation schemas, Error handling middleware, Logging, Environment config, Database connection, API docs, Unit tests, Integration tests
- Do NOT mix business logic into controllers (controllers should only handle HTTP request/response)
- Do NOT put database queries in controllers (use Repository layer)
- Do NOT skip Repository layer (required for data access operations)
- Do NOT skip Service layer (required for business logic)
- Backend steps should have 12-18 steps
- Each step should have 2-5 atomic sub-steps
- Use category "backend" for backend steps

**FRONTEND (React + TypeScript + Vite):**
- MANDATORY: Use the FRONTEND PLANNING GUIDELINES checklist (15 mandatory categories)
- MUST include: Types, API Config, UI Components, Validation, Services, Hooks, Layouts, Feature Components, Pages, Routing, Guards, Context, Error Handling, Loading States, Token Management
- Do NOT skip infrastructure steps (types, API config, validation, error handling, etc.)
- Follow the recommended step ordering: Types → API Config → UI Components → Validation → Services → Hooks → Layouts → Feature Components → Pages → Routing → Guards → Context → Error Handling → Loading → Tokens → Integration
- Frontend steps should have 10-16 steps
- Each step should have 2-4 atomic sub-steps
- Use category "frontend" for frontend steps

**COMBINED:**
- Total should be 18-25+ steps combining both backend and frontend
- Order backend steps first, then frontend steps
- Ensure proper dependencies between backend and frontend (e.g., frontend API service depends on backend routes)
"""

    return prompt
