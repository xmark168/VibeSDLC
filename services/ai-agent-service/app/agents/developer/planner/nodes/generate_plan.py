"""
Generate Plan Node

PHASE 4: Implementation Planning - Create detailed implementation plan
"""

from langchain_core.messages import AIMessage

from ..state import ImplementationPlan, PlannerState


def generate_plan(state: PlannerState) -> PlannerState:
    """
    Generate Plan node - PHASE 4: Create detailed implementation plan.

    Tasks:
    1. Determine task complexity score (1-10)
    2. Create simple or complex plan based on complexity
    3. Include implementation steps với detailed guidance
    4. Estimate effort và story points
    5. Document risks và assumptions
    6. Structure output trong ImplementationPlan model

    Args:
        state: PlannerState với dependency_mapping

    Returns:
        Updated PlannerState với implementation_plan populated
    """
    print("\n" + "=" * 80)
    print("PLAN: GENERATE PLAN NODE - Phase 4: Implementation Planning")
    print("=" * 80)

    try:
        task_requirements = state.task_requirements
        dependency_mapping = state.dependency_mapping
        codebase_analysis = state.codebase_analysis

        print(f"🎯 Generating implementation plan for: {task_requirements.task_id}")
        print(f"📁 Files to create: {len(codebase_analysis.files_to_create)}")
        print(f"✏️  Files to modify: {len(codebase_analysis.files_to_modify)}")
        print(f"📦 Affected modules: {len(codebase_analysis.affected_modules)}")

        # Use LLM for plan generation with Chain of Vibe methodology
        import json
        import os

        from langchain_openai import ChatOpenAI

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        # Create Chain of Vibe prompt for plan generation
        plan_prompt = f"""# CHAIN OF VIBE IMPLEMENTATION PLANNING

You are an expert implementation planner using the "Chain of Vibe" methodology for hierarchical, incremental task decomposition.

## METHODOLOGY: Chain of Vibe Task Decomposition

**Core Principles:**
1. **Hierarchical Breakdown**: Each major step decomposes into atomic sub-steps
2. **Logical Dependencies**: Steps ordered by technical dependencies (data → logic → UI)
3. **Actionable Granularity**: Each sub-step is a single, testable change (~15-30 minutes)
4. **Incremental Execution**: Each sub-step produces working code that can be committed
5. **Full-Stack Coverage**: Unified plan covering backend → frontend → integration

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

Codebase Analysis:
Files to Create: {len(codebase_analysis.files_to_create)}
{json.dumps([f["path"] for f in codebase_analysis.files_to_create], indent=2)}

Files to Modify: {len(codebase_analysis.files_to_modify)}
{json.dumps([f["path"] for f in codebase_analysis.files_to_modify], indent=2)}

Affected Modules:
{json.dumps(codebase_analysis.affected_modules, indent=2)}

API Endpoints:
{json.dumps(codebase_analysis.api_endpoints, indent=2)}

Database Changes:
{json.dumps(codebase_analysis.database_changes, indent=2)}

Dependency Mapping:
{dependency_mapping.model_dump_json(indent=2)}

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
          "description": "Add JWT and password hashing libraries to package.json",
          "action_type": "setup|create|modify|test",
          "files_affected": ["package.json"],
          "test":"Run npm install and verify jsonwebtoken and bcrypt are installed correctly"
        }},
        {{
                    "sub_step": "1.2",
          "title": "Create JWT utility functions",
          "description": "Implement signToken() and verifyToken() helper functions",
          "action_type": "create",
          "files_affected": ["src/utils/jwt.js"],
          "test": "Import and call signToken() with test payload, verify it returns valid JWT string"
        }},
        {{
                    "sub_step": "1.3",
          "title": "Add JWT_SECRET to environment config",
          "description": "Add JWT_SECRET variable to .env and config loader",
          "action_type": "modify",
          "files_affected": [".env.example", "src/config/environment.js"],
          "test": "Start application and verify JWT_SECRET is loaded correctly from environment"
        }}
      ],
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
          "description": "Setup POST /api/auth/login route with Express router",
          "action_type": "create",
          "files_affected": ["src/routes/auth.routes.js", "src/app.js"],
          "test": "Send POST request to /api/auth/login and verify route is accessible (404 → 400/500)"
        }},
        {{
                    "sub_step": "2.2",
          "title": "Implement login controller logic",
          "description": "Create controller to validate credentials and generate JWT",
          "action_type": "create",
          "files_affected": ["src/controllers/auth.controller.js"],
          "test": "Call login controller with test credentials and verify JWT token is generated"
        }},
        {{
                    "sub_step": "2.3",
          "title": "Add request validation middleware",
          "description": "Validate email format and password presence",
          "action_type": "create",
          "files_affected": ["src/middleware/validation.js"],
          "test": "Send invalid request (missing email/password) and verify 400 validation error"
        }}
      ],
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
          "description": "Setup functional component with form fields and basic styling",
          "action_type": "create",
          "files_affected": ["src/components/LoginForm.jsx"],
          "test": "Import and render LoginForm component, verify form fields are displayed correctly"
        }},
        {{
                    "sub_step": "3.2",
          "title": "Add form validation logic",
          "description": "Implement client-side validation with error messages",
          "action_type": "modify",
          "files_affected": ["src/components/LoginForm.jsx"],
          "test": "Submit form with invalid data and verify validation error messages appear"
        }},
        {{
                    "sub_step": "3.3",
          "title": "Add loading and error states",
          "description": "Implement loading spinner and API error display",
          "action_type": "modify",
          "files_affected": ["src/components/LoginForm.jsx"],
          "test": "Trigger loading state and verify spinner appears, trigger error and verify error message displays"
        }}
      ],
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
          "description": "Implement API client for authentication endpoints",
          "action_type": "create",
          "files_affected": ["src/services/auth.service.js"],
          "test": "Call auth service login method with test data and verify API request is made correctly"
        }},
        {{
                    "sub_step": "4.2",
          "title": "Create useAuth custom hook",
          "description": "Build hook managing auth state and login function",
          "action_type": "create",
          "files_affected": ["src/hooks/useAuth.js"],
          "test": "Use useAuth hook in test component and verify auth state and login function work"
        }},
        {{
                    "sub_step": "4.3",
          "title": "Add token storage logic",
          "description": "Implement localStorage for JWT persistence",
          "action_type": "modify",
          "files_affected": ["src/hooks/useAuth.js", "src/services/auth.service.js"],
          "test": "Login and verify JWT token is stored in localStorage, refresh page and verify token persists"
        }}
      ],
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
          "description": "Verify complete flow with valid credentials",
          "action_type": "test",
          "files_affected": ["tests/integration/auth.test.js"],
          "test": "Run integration test and verify successful login returns JWT token and user data"
        }},
        {{
                    "sub_step": "5.2",
          "title": "Test error scenarios",
          "description": "Verify handling of invalid credentials and network errors",
          "action_type": "test",
          "files_affected": ["tests/integration/auth.test.js"],
          "test": "Run error scenario tests and verify proper error handling and user feedback"
        }}
      ],
      "dependencies": [4],
      "estimated_hours": 0.7,
      "complexity": "low"
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

  "total_estimated_hours": 4.4,
  "story_points": 5,

  "execution_order": [
    "Execute steps sequentially: 1 → 2 → 3 → 4 → 5",
    "Within each step, execute sub-steps in order",
    "Test after each sub-step before proceeding",
    "Commit code after each completed sub-step"
  ]
}}
```

## CRITICAL REQUIREMENTS FOR INCREMENTAL EXECUTION

### Sub-Step Design Rules:
1. **Atomic Changes**: Each sub-step modifies 1-3 files maximum
2. **Single Responsibility**: One clear action per sub-step
3. **Testable**: Each sub-step has a verification method
4. **Committable**: Code should compile/run after each sub-step
5. **Time-Boxed**: 15-30 minutes per sub-step (never exceed 45 min)

### Action Types:
- `setup`: Install dependencies, configure environment
- `create`: Create new files/functions/components
- `modify`: Edit existing code incrementally
- `test`: Write or run tests

### Code Changes Format:
Each sub-step must specify `code_changes` with:
- `type`: What kind of change (create_file, modify_function, add_route, etc.)
- `specifics`: Exact functions/components/endpoints being added/modified
- `template`: (optional) Reference to code template to use

### Test Field Requirements:
Each sub-step must include a "test" field with immediate verification:
- **Specific and actionable**: Clear instructions for verifying completion
- **Quick verification**: Should take 1-3 minutes to execute
- **Immediate feedback**: Verify the sub-step works before proceeding
- **Examples**:
  - Setup: "Run npm install and verify package is installed correctly"
  - Create: "Import function and call with test data, verify expected output"
  - Modify: "Start application and verify new configuration is loaded"
  - Test: "Run test suite and verify all tests pass"

## DEPENDENCY ORDERING RULES

**Backend Execution Order:**
1. Database/Schema setup
2. Models and data access layer
3. Service layer (business logic)
4. Controllers
5. Routes and middleware
6. API documentation

**Frontend Execution Order:**
1. API service layer
2. Custom hooks/state management
3. Component structure (presentational)
4. Component logic (interactive)
5. Form validation
6. Integration with backend

**Cross-Stack Dependencies:**
- Frontend steps CANNOT start until their backend API dependencies are complete
- Example: LoginForm (step 3) requires login endpoint (step 2)

## EXAMPLES

### Good Sub-Step (Atomic, Testable):
```json
{{
            "sub_step": "2.1",
  "title": "Create login route handler",
  "description": "Add POST /api/auth/login route to Express router",
  "action_type": "create",
  "files_affected": ["src/routes/auth.routes.js"],
  "test": "Send POST to /api/auth/login and verify route is accessible (404 → 400/500)"
}}
```

### Bad Sub-Step (Too Vague):
```json
{{
            "sub_step": "2.1",
  "title": "Setup authentication",
  "description": "Create authentication system",
  // ❌ Too broad, multiple files, no clear verification
}}
```

## GENERATE PLAN NOW

Analyze the task requirements and generate a complete Chain of Vibe implementation plan with:
- Clear step hierarchy (major steps → atomic sub-steps)
- Logical dependency ordering
- Specific file changes for each sub-step
- **"test" field for each sub-step** with immediate verification instructions
- Realistic time estimates (sub-steps: 15-30 min, steps: 0.5-2 hours)

Output valid JSON following the exact format above.
"""

        print("🤖 Calling LLM for Chain of Vibe plan generation...")

        # Call LLM
        response = llm.invoke(plan_prompt)
        llm_output = response.content

        print(f"📝 LLM Response: {llm_output[:200]}...")

        # Parse JSON response from LLM - Handle markdown code blocks
        try:
            # Strip markdown code blocks if present
            cleaned_output = llm_output.strip()
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output[7:]  # Remove ```json
            elif cleaned_output.startswith("```"):
                cleaned_output = cleaned_output[3:]  # Remove ```
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3]  # Remove trailing ```
            cleaned_output = cleaned_output.strip()

            print(f"🧹 Cleaned LLM output: {cleaned_output[:100]}...")

            parsed_plan = json.loads(cleaned_output)

            # Extract simplified plan data
            complexity_score = parsed_plan.get("complexity_score", 5)
            plan_type = parsed_plan.get("plan_type", "simple")

            # Convert steps to ImplementationStep objects
            from ..state import ImplementationStep

            steps_data = parsed_plan.get("steps", [])
            implementation_steps = []

            for step_data in steps_data:
                step = ImplementationStep(
                    step=step_data.get("step", 0),
                    title=step_data.get("title", ""),
                    description=step_data.get("description", ""),
                    category=step_data.get("category", "backend"),
                    sub_steps=step_data.get("sub_steps", []),
                    dependencies=step_data.get("dependencies", []),
                    estimated_hours=step_data.get("estimated_hours", 0.0),
                    complexity=step_data.get("complexity", "medium"),
                )
                implementation_steps.append(step)

            # Extract other simplified fields
            functional_requirements = parsed_plan.get("functional_requirements", [])
            database_changes = parsed_plan.get("database_changes", [])
            external_dependencies = parsed_plan.get("external_dependencies", [])
            internal_dependencies = parsed_plan.get("internal_dependencies", [])
            execution_order = parsed_plan.get("execution_order", [])
            total_estimated_hours = parsed_plan.get("total_estimated_hours", 0.0)
            story_points = parsed_plan.get("story_points", 0)

            print(
                f"✅ Successfully parsed Chain of Vibe plan with complexity {complexity_score}/10, {len(implementation_steps)} steps, {total_estimated_hours}h"
            )

        except json.JSONDecodeError as e:
            print(f"❌ LLM response not valid JSON after cleaning: {e}")
            print(f"Raw LLM output: {llm_output[:200]}...")
            print(
                f"Cleaned output: {cleaned_output[:200] if 'cleaned_output' in locals() else 'N/A'}..."
            )
            # Fallback for JSON parsing failure
            complexity_score = 5
            plan_type = "simple"
            implementation_steps = []
            functional_requirements = task_requirements.requirements or []
            database_changes = []
            external_dependencies = []
            internal_dependencies = []
            execution_order = []
            total_estimated_hours = 4.0
            story_points = 3

        print(f"INFO: Complexity Score: {complexity_score}/10")

        # Use implementation steps from LLM if available, otherwise create minimal fallback
        if not implementation_steps:
            print("⚠️ No implementation steps from LLM, using minimal fallback")
            from ..state import ImplementationStep

            fallback_step = ImplementationStep(
                step=1,
                title="Implement feature",
                description="Complete the requested feature implementation",
                category="backend",
                sub_steps=[],
                dependencies=[],
                estimated_hours=total_estimated_hours,
                complexity="medium",
            )
            implementation_steps = [fallback_step]

        # Calculate totals if not provided
        if total_estimated_hours == 0:
            total_estimated_hours = sum(
                step.estimated_hours for step in implementation_steps
            )

        if story_points == 0:
            story_points = estimate_story_points(
                complexity_score, total_estimated_hours
            )

        # Create simplified ImplementationPlan object
        implementation_plan = ImplementationPlan(
            task_id=task_requirements.task_id,
            description=task_requirements.task_title,
            complexity_score=complexity_score,
            plan_type=plan_type,
            functional_requirements=functional_requirements,
            steps=implementation_steps,
            database_changes=database_changes,
            external_dependencies=external_dependencies,
            internal_dependencies=internal_dependencies,
            execution_order=execution_order,
            total_estimated_hours=total_estimated_hours,
            story_points=story_points,
        )

        # Update state
        state.implementation_plan = implementation_plan
        state.current_phase = "validate_plan"
        state.status = "plan_generated"

        # Store in tools_output
        state.tools_output["implementation_plan"] = implementation_plan.model_dump()

        # Add AI message
        plan_result = {
            "phase": "Chain of Vibe Implementation Planning",
            "plan_type": plan_type,
            "complexity_score": complexity_score,
            "total_steps": len(implementation_steps),
            "estimated_hours": total_estimated_hours,
            "story_points": story_points,
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 3: Chain of Vibe Implementation Planning - COMPLETED

Plan Results:
{json.dumps(plan_result, indent=2)}

Implementation Steps:
{chr(10).join(f"{step.step}. {step.title} ({step.estimated_hours}h)" for step in implementation_steps)}

Total Effort: {total_estimated_hours} hours ({story_points} story points)

Ready to proceed to Plan Validation."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Chain of Vibe implementation plan generated successfully")
        print(f"PLAN: Plan Type: {plan_type}")
        print(f"INFO: Complexity: {complexity_score}/10")
        print(f"TIME:  Total Hours: {total_estimated_hours}")
        print(f"SCORE: Story Points: {story_points}")
        print(f"ITER: Next Phase: {state.current_phase}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in plan generation: {e}")
        print("🔍 DEBUG: Exception details:")
        import traceback

        traceback.print_exc()

        # Set error status
        state.status = "error_plan_generation"
        state.error_message = f"Plan generation failed: {str(e)}"

        # Ensure implementation_plan is set to empty but valid structure
        # This prevents downstream nodes from accessing uninitialized fields
        state.implementation_plan = ImplementationPlan()

        # Set phase to finalize để handle error properly
        state.current_phase = "finalize"

        print(
            "❌ GENERATE PLAN FAILED: Set empty implementation_plan and routing to finalize"
        )
        print(f"   Error status: {state.status}")
        print(f"   Error message: {state.error_message}")

        return state


def estimate_story_points(complexity_score: int, total_hours: float) -> int:
    """Estimate story points using Fibonacci sequence based on complexity and hours."""
    # Fibonacci sequence: 1, 2, 3, 5, 8, 13, 21
    fibonacci = [1, 2, 3, 5, 8, 13, 21]

    # Base estimation on complexity score and hours
    if complexity_score <= 2 and total_hours <= 4:
        return 1
    elif complexity_score <= 4 and total_hours <= 8:
        return 2
    elif complexity_score <= 6 and total_hours <= 16:
        return 3
    elif complexity_score <= 7 and total_hours <= 24:
        return 5
    elif complexity_score <= 8 and total_hours <= 40:
        return 8
    elif complexity_score <= 9 and total_hours <= 60:
        return 13
    else:
        return 21


# Chain of Vibe methodology implementation complete
