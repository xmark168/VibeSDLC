"""
Planner Agent Prompts

Contains all prompt templates for the Planner Agent.
"""

import json


def create_chain_of_vibe_prompt(
    state,
    task_requirements,
    detailed_codebase_context: str,
    project_structure: dict,
    architecture_guidelines_text: str,
) -> str:
    """
    Create Chain of Vibe implementation planning prompt.

    Args:
        state: PlannerState with tech_stack
        task_requirements: TaskRequirements object
        detailed_codebase_context: Detailed context string
        project_structure: Project structure dict
        architecture_guidelines_text: Architecture guidelines text

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
      "title": "Setup JWT authentication foundation",
      "description": "Install dependencies and configure JWT infrastructure",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "1.1",
          "title": "Install jsonwebtoken and bcrypt libraries",
          "description": "Add JWT and password hashing libraries to package.json"
        }},
        {{
          "sub_step": "1.2",
          "title": "Create JWT utility functions",
          "description": "Implement signToken() and verifyToken() helper functions"
        }},
        {{
          "sub_step": "1.3",
          "title": "Add JWT_SECRET to environment config",
          "description": "Add JWT_SECRET variable to .env and config loader"
        }}
      ]
    }},
    {{
      "step": 2,
      "title": "Implement login API endpoint",
      "description": "Create authentication endpoint with credential validation",
      "category": "backend",
      "sub_steps": [
        {{
          "sub_step": "2.1",
          "title": "Create auth router and login route",
          "description": "Setup POST /api/auth/login route with Express router"
        }},
        {{
          "sub_step": "2.2",
          "title": "Implement login controller logic",
          "description": "Create controller to validate credentials and generate JWT"
        }},
        {{
          "sub_step": "2.3",
          "title": "Add request validation middleware",
          "description": "Validate email format and password presence"
        }}
      ]
    }},
    {{
      "step": 3,
      "title": "Create frontend Login Form component",
      "description": "Build React login form with validation and state management",
      "category": "frontend",
      "sub_steps": [
        {{
          "sub_step": "3.1",
          "title": "Create LoginForm component structure",
          "description": "Setup functional component with form fields and basic styling"
        }},
        {{
          "sub_step": "3.2",
          "title": "Add form validation logic",
          "description": "Implement client-side validation with error messages"
        }},
        {{
          "sub_step": "3.3",
          "title": "Add loading and error states",
          "description": "Implement loading spinner and API error display"
        }}
      ]
    }},
    {{
      "step": 4,
      "title": "Implement authentication state management",
      "description": "Create custom hook and API service for auth flow",
      "category": "frontend",
      "sub_steps": [
        {{
          "sub_step": "4.1",
          "title": "Create auth API service",
          "description": "Implement API client for authentication endpoints"
        }},
        {{
          "sub_step": "4.2",
          "title": "Create useAuth custom hook",
          "description": "Build hook managing auth state and login function"
        }},
        {{
          "sub_step": "4.3",
          "title": "Add token storage logic",
          "description": "Implement localStorage for JWT persistence"
        }}
      ]
    }},
    {{
      "step": 5,
      "title": "End-to-end integration testing",
      "description": "Test complete authentication flow from UI to backend",
      "category": "integration",
      "sub_steps": [
        {{
          "sub_step": "5.1",
          "title": "Test successful login flow",
          "description": "Verify complete flow with valid credentials"
        }},
        {{
          "sub_step": "5.2",
          "title": "Test error scenarios",
          "description": "Verify handling of invalid credentials and network errors"
        }}
      ]
    }}
  ],

  "database_changes": [
    {{
      "change": "Add users table",
      "fields": ["id", "email", "password_hash", "created_at", "updated_at"],
      "affected_step": 1
    }}
  ],

  "external_dependencies": [
    {{"package": "jsonwebtoken", "version": "^9.0.0", "purpose": "JWT token generation"}},
    {{"package": "bcrypt", "version": "^5.1.0", "purpose": "Password hashing"}}
  ],

  "internal_dependencies": [
    {{"module": "User model", "required_by_step": 2}},
    {{"module": "Validation middleware", "required_by_step": 2}}
  ],

  "story_points": 5,

  "execution_order": [
    "Execute steps sequentially: 1 → 2 → 3 → 4 → 5",
    "Within each step, execute sub-steps in order",
    "Test after each sub-step before proceeding",
    "Commit code after each completed sub-step"
  ]
}}
```

## CRITICAL REQUIREMENTS

### Core Principles:
1. **Hierarchical Breakdown**: Each major step decomposes into atomic sub-steps
2. **Logical Dependencies**: Steps ordered by technical dependencies (data → logic → UI)
3. **Actionable Granularity**: Each sub-step is a single, testable change
4. **Incremental Execution**: Each sub-step produces working code that can be committed
5. **Full-Stack Coverage**: Unified plan covering backend → frontend → integration

### JSON Schema Rules:
1. **Steps**: Each step MUST have: step (number), title, description, category, sub_steps (array)
2. **Sub-steps**: Each sub-step MUST have ONLY 3 fields:
   - "sub_step": "X.Y" (string format)
   - "title": "Brief action title"
   - "description": "Detailed description"
3. **Categories**: Use "backend", "frontend", "database", "testing", or "integration"
4. **Database Changes**: Include change, fields (array), affected_step
5. **Dependencies**:
   - external_dependencies: package, version, purpose
   - internal_dependencies: module, required_by_step
6. **Execution Order**: Array of strings describing sequential execution flow
7. **Story Points**: Use Fibonacci sequence (1, 2, 3, 5, 8, 13, 21)

## GENERATE PLAN NOW

Analyze the task requirements and generate a complete Chain of Vibe implementation plan.

**STRICT OUTPUT RULES:**
- Output ONLY valid JSON, no markdown code blocks
- Follow the EXACT schema shown in the example above
- Do NOT add extra fields to sub-steps (only sub_step, title, description)
- Do NOT add file_changes, estimated_time, or any other fields
- Ensure all JSON is properly formatted and parseable
"""

    return prompt
