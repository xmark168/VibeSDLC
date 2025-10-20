"""
Demo script to show how the raw JSON output will look like.
"""

import json


def demo_raw_json_output():
    """Demo the raw JSON output format."""

    # Sample planner result (similar to what you provided)
    sample_result = {
        "success": True,
        "final_plan": {
            "task_info": {
                "task_id": "TASK-001",
                "description": "Implement user registration functionality with validation, password hashing, and email verification",
                "complexity_score": 7,
                "plan_type": "complex",
            },
            "requirements": {
                "functional_requirements": [
                    "Users can register with email and password",
                    "Password validation includes minimum 8 characters, uppercase, lowercase, number, special character",
                    "Email validation ensures proper format and uniqueness",
                    "Password is hashed using bcrypt before storing in database",
                ],
                "acceptance_criteria": [
                    "Given a user registers with email and password, when they submit the registration form, then the registration endpoint accepts email, password, and confirm_password",
                    "Given a successful registration, when the registration is complete, then a JWT token is returned",
                    "Given invalid input, when validation fails, then appropriate error messages are returned",
                ],
                "business_rules": {
                    "Password Security": "Passwords must be hashed using bcrypt with minimum 8 characters",
                    "Email Uniqueness": "Email addresses must be unique across all users",
                },
                "technical_specs": {
                    "framework": "FastAPI for API endpoints",
                    "database": "PostgreSQL database with SQLModel",
                    "authentication": "JWT tokens for session management",
                },
                "constraints": [
                    "Must maintain backward compatibility",
                    "Must follow existing code style and patterns",
                    "Must include appropriate error handling",
                ],
            },
            "implementation": {
                "approach": {
                    "strategy": "Develop a comprehensive user registration system with security best practices",
                    "pattern": "Follow existing patterns in the codebase for services and API endpoints",
                    "architecture_alignment": "Aligns with the current microservices architecture",
                },
                "steps": [
                    {
                        "step": 1,
                        "title": "Create User model",
                        "description": "Define User model with authentication fields",
                        "action": "Create app/models/user.py with User SQLModel class",
                        "files": ["app/models/user.py"],
                        "estimated_hours": 1.5,
                        "complexity": "medium",
                        "dependencies": [],
                        "blocking": True,
                        "validation": "Confirm User model can be imported and instantiated",
                        "error_handling": [
                            "Handle field validation errors",
                            "Handle database connection errors",
                        ],
                        "code_template": "class User(SQLModel, table=True): ...",
                    },
                    {
                        "step": 2,
                        "title": "Create authentication service",
                        "description": "Implement password hashing and validation logic",
                        "action": "Create app/services/auth_service.py with authentication methods",
                        "files": ["app/services/auth_service.py"],
                        "estimated_hours": 2.0,
                        "complexity": "high",
                        "dependencies": [1],
                        "blocking": True,
                        "validation": "Unit tests for password hashing and validation must pass",
                        "error_handling": [
                            "Handle bcrypt errors",
                            "Handle invalid password formats",
                        ],
                        "code_template": "def hash_password(password: str) -> str: ...",
                    },
                    {
                        "step": 3,
                        "title": "Create API schemas",
                        "description": "Define Pydantic schemas for registration requests/responses",
                        "action": "Create app/schemas/auth.py with request/response models",
                        "files": ["app/schemas/auth.py"],
                        "estimated_hours": 1.0,
                        "complexity": "low",
                        "dependencies": [],
                        "blocking": False,
                        "validation": "Schema validation tests must pass",
                        "error_handling": ["Handle schema validation errors"],
                        "code_template": "class UserRegistrationRequest(BaseModel): ...",
                    },
                    {
                        "step": 4,
                        "title": "Create authentication routes",
                        "description": "Implement registration and login endpoints",
                        "action": "Create app/api/routes/auth.py with FastAPI endpoints",
                        "files": ["app/api/routes/auth.py"],
                        "estimated_hours": 2.5,
                        "complexity": "high",
                        "dependencies": [1, 2, 3],
                        "blocking": False,
                        "validation": "Integration tests for endpoints must pass",
                        "error_handling": [
                            "Handle duplicate email errors",
                            "Handle validation errors",
                        ],
                        "code_template": "@router.post('/register')",
                    },
                    {
                        "step": 5,
                        "title": "Update main app",
                        "description": "Register authentication router in main FastAPI app",
                        "action": "Modify app/main.py to include auth router",
                        "files": ["app/main.py"],
                        "estimated_hours": 0.5,
                        "complexity": "low",
                        "dependencies": [4],
                        "blocking": False,
                        "validation": "App starts successfully with new routes",
                        "error_handling": ["Handle router registration errors"],
                        "code_template": "app.include_router(auth_router, prefix='/api/auth')",
                    },
                    {
                        "step": 6,
                        "title": "Create comprehensive tests",
                        "description": "Implement unit and integration tests for authentication",
                        "action": "Create tests/test_auth.py with comprehensive test coverage",
                        "files": ["tests/test_auth.py"],
                        "estimated_hours": 3.0,
                        "complexity": "medium",
                        "dependencies": [1, 2, 3, 4],
                        "blocking": False,
                        "validation": "All tests pass with >90% coverage",
                        "error_handling": ["Handle test setup/teardown errors"],
                        "code_template": "def test_user_registration_success(): ...",
                    },
                ],
                "execution_order": [
                    {
                        "step": 1,
                        "action": "Create User model",
                        "reason": "Foundation for all other components",
                        "blocking": True,
                        "depends_on": [],
                        "files": ["app/models/user.py"],
                    },
                    {
                        "step": 2,
                        "action": "Create authentication service",
                        "reason": "Core business logic",
                        "blocking": True,
                        "depends_on": [1],
                        "files": ["app/services/auth_service.py"],
                    },
                    {
                        "step": 3,
                        "action": "Create API schemas",
                        "reason": "Request/response validation",
                        "blocking": False,
                        "depends_on": [],
                        "files": ["app/schemas/auth.py"],
                    },
                    {
                        "step": 4,
                        "action": "Create authentication routes",
                        "reason": "API endpoints",
                        "blocking": False,
                        "depends_on": [1, 2, 3],
                        "files": ["app/api/routes/auth.py"],
                    },
                    {
                        "step": 5,
                        "action": "Update main app",
                        "reason": "Integration",
                        "blocking": False,
                        "depends_on": [4],
                        "files": ["app/main.py"],
                    },
                    {
                        "step": 6,
                        "action": "Create tests",
                        "reason": "Quality assurance",
                        "blocking": False,
                        "depends_on": [1, 2, 3, 4],
                        "files": ["tests/test_auth.py"],
                    },
                ],
                "parallel_opportunities": [
                    {"steps": [3], "reason": "Schemas can be developed independently"},
                    {
                        "steps": [6],
                        "reason": "Tests can be written in parallel with implementation",
                    },
                ],
                "execution_strategy": {
                    "phases": [
                        {
                            "phase": 1,
                            "name": "Foundation",
                            "steps": [1, 2],
                            "blocking": True,
                        },
                        {
                            "phase": 2,
                            "name": "Implementation",
                            "steps": [3, 4, 5],
                            "blocking": False,
                        },
                        {
                            "phase": 3,
                            "name": "Testing",
                            "steps": [6],
                            "blocking": False,
                        },
                    ]
                },
            },
            "file_changes": {
                "files_to_create": [
                    {
                        "path": "app/models/user.py",
                        "reason": "User model with authentication fields",
                        "template": "Follow SQLModel patterns from existing models",
                        "estimated_lines": 100,
                        "complexity": "medium",
                    },
                    {
                        "path": "app/services/auth_service.py",
                        "reason": "Authentication business logic and password hashing",
                        "template": "Follow service patterns from existing services",
                        "estimated_lines": 150,
                        "complexity": "high",
                    },
                    {
                        "path": "app/schemas/auth.py",
                        "reason": "Pydantic schemas for authentication requests/responses",
                        "template": "Follow schema patterns from existing schemas",
                        "estimated_lines": 80,
                        "complexity": "low",
                    },
                    {
                        "path": "app/api/routes/auth.py",
                        "reason": "Authentication endpoints for registration and login",
                        "template": "Follow router patterns from existing routes",
                        "estimated_lines": 200,
                        "complexity": "high",
                    },
                    {
                        "path": "tests/test_auth.py",
                        "reason": "Unit tests for authentication functionality",
                        "template": "Follow test patterns from existing tests",
                        "estimated_lines": 300,
                        "complexity": "medium",
                    },
                ],
                "files_to_modify": [
                    {
                        "path": "app/main.py",
                        "lines": [20, 25],
                        "changes": "Add authentication router to FastAPI app",
                        "complexity": "low",
                        "risk": "low",
                    },
                    {
                        "path": "requirements.txt",
                        "lines": [-1],
                        "changes": "Add bcrypt and python-jose dependencies for authentication",
                        "complexity": "low",
                        "risk": "low",
                    },
                ],
                "affected_modules": [
                    "app.models",
                    "app.services",
                    "app.schemas",
                    "app.api",
                    "tests",
                ],
            },
            "infrastructure": {
                "database_changes": [
                    {
                        "type": "table",
                        "name": "users",
                        "operation": "create",
                        "details": "Create users table with id, email, password_hash, created_at, updated_at fields",
                        "migration_complexity": "medium",
                    }
                ],
                "api_endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/auth/register",
                        "description": "User registration endpoint",
                    },
                    {
                        "method": "POST",
                        "path": "/api/auth/login",
                        "description": "User login endpoint",
                    },
                ],
                "external_dependencies": [
                    "bcrypt",
                    "python-jose[cryptography]",
                    "passlib[bcrypt]",
                ],
                "internal_dependencies": [
                    "app.models.user",
                    "app.services.auth_service",
                    "app.schemas.auth",
                ],
            },
            "metadata": {
                "planner_version": "1.0",
                "planning_iterations": 2,
                "validation_passed": True,
                "created_by": "planner_subagent",
                "execution_time": 18.5,
                "tokens_used": 1450,
            },
        },
        "execution_time": 18.5,
        "tokens_used": 1450,
        "planner_state": "completed",
        "validation_results": {
            "plan_quality": "high",
            "completeness": "complete",
            "feasibility": "feasible",
        },
    }

    print("🔍 PLANNER AGENT STATE JSON DEBUG - RAW OUTPUT")
    print("=" * 80)

    print("\n📋 FULL RAW JSON STRUCTURE:")
    print("planner_result = {")

    # Print clean JSON format
    final_plan = sample_result.get("final_plan", {})
    try:
        print(json.dumps(final_plan, indent=2, ensure_ascii=False))
    except Exception as e:
        # Fallback to full result if final_plan fails
        try:
            print(json.dumps(sample_result, indent=2, ensure_ascii=False, default=str))
        except Exception as json_error:
            print(f"❌ Could not format result: {e}, {json_error}")
            print(f"Raw result: {sample_result}")

    print("}")

    # Quick summary
    final_plan = sample_result.get("final_plan", {})
    if "file_changes" in final_plan:
        file_changes = final_plan["file_changes"]
        files_to_create = file_changes.get("files_to_create", [])
        files_to_modify = file_changes.get("files_to_modify", [])

        print("\n📊 QUICK SUMMARY:")
        print(f"  - files_to_create: {len(files_to_create)} files")
        print(f"  - files_to_modify: {len(files_to_modify)} files")
        print("✅ File operations found - should pass validation")

    print("=" * 80)


if __name__ == "__main__":
    demo_raw_json_output()
