"""
Test Implementor Agent

Test file để verify Implementor Agent functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.developer.implementor.agent import ImplementorAgent


def test_implementor_new_project():
    """Test implementor với new project scenario."""

    print("\n🧪 Testing New Project Scenario...")

    # Create test directory structure

    test_dir = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo\be\nodejs\express-basic"

    implementor = ImplementorAgent(model="gpt-4o")

    # Mock plan for new FastAPI project
    new_project_plan = {
        "task_id": "TSK-7457",
        "description": "Task: Implement user registration functionality\nTask Description: Create user registration API endpo...",
        "complexity_score": 7,
        "plan_type": "complex",
        "functional_requirements": [
            "Create a POST /api/auth/register endpoint that accepts email, password, and confirm_password.",
            "Implement password validation to ensure it includes a minimum of 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character.",
            "Ensure email validation checks for proper format and uniqueness.",
            "Hash the password using bcrypt before storing it in the database.",
            "Store user data in the database with a created_at timestamp.",
            "Return a JWT token upon successful registration.",
            "Return appropriate error messages for validation failures.",
            "Include comprehensive unit tests for all scenarios.",
            "Update API documentation with endpoint details.",
        ],
        "steps": [
            {
                "step": 1,
                "title": "Create User Model",
                "description": "Define the User model schema with Mongoose including validation rules.",
                "category": "database",
                "sub_steps": [
                    {
                        "sub_step": "1.1",
                        "title": "Define User schema",
                        "description": "Create a Mongoose schema for User with fields: name, email, password, and timestamps.",
                    },
                    {
                        "sub_step": "1.2",
                        "title": "Add unique index on email",
                        "description": "Ensure the email field is unique to prevent duplicate registrations.",
                    },
                ],
            },
            {
                "step": 2,
                "title": "Create User Repository",
                "description": "Implement the User repository for database operations related to users.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "2.1",
                        "title": "Implement findByEmail method",
                        "description": "Create a method to find a user by email in the User repository.",
                    },
                    {
                        "sub_step": "2.2",
                        "title": "Implement create method",
                        "description": "Create a method to save a new user in the User repository.",
                    },
                ],
            },
            {
                "step": 3,
                "title": "Create Auth Service",
                "description": "Implement business logic for user registration and token generation.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "3.1",
                        "title": "Implement registerUser method",
                        "description": "Create a method to handle user registration, including validation and password hashing.",
                    },
                    {
                        "sub_step": "3.2",
                        "title": "Generate JWT token",
                        "description": "Implement logic to generate a JWT token upon successful registration.",
                    },
                ],
            },
            {
                "step": 4,
                "title": "Create Auth Controller",
                "description": "Implement the controller to handle incoming registration requests.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "4.1",
                        "title": "Implement registerUser controller",
                        "description": "Create a controller method to process registration requests and return responses.",
                    },
                    {
                        "sub_step": "4.2",
                        "title": "Handle errors in controller",
                        "description": "Ensure proper error handling and response formatting in the controller.",
                    },
                ],
            },
            {
                "step": 5,
                "title": "Create Auth Routes",
                "description": "Define the API routes for user registration.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "5.1",
                        "title": "Setup POST /api/auth/register route",
                        "description": "Create the route for user registration and link it to the controller.",
                    },
                    {
                        "sub_step": "5.2",
                        "title": "Add request validation middleware",
                        "description": "Implement middleware to validate request body using Joi.",
                    },
                ],
            },
            {
                "step": 6,
                "title": "Implement Unit Tests",
                "description": "Create tests for the registration functionality.",
                "category": "testing",
                "sub_steps": [
                    {
                        "sub_step": "6.1",
                        "title": "Test successful registration",
                        "description": "Write tests to verify successful user registration and token generation.",
                    },
                    {
                        "sub_step": "6.2",
                        "title": "Test validation errors",
                        "description": "Write tests to check for validation errors on email and password.",
                    },
                    {
                        "sub_step": "6.3",
                        "title": "Test duplicate email error",
                        "description": "Write tests to verify handling of duplicate email registrations.",
                    },
                ],
            },
            {
                "step": 7,
                "title": "Update API Documentation",
                "description": "Document the new registration endpoint in the API documentation.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "7.1",
                        "title": "Add endpoint details",
                        "description": "Include details about the /api/auth/register endpoint in the API documentation.",
                    }
                ],
            },
        ],
        "database_changes": [
            {
                "change": "Add users collection",
                "fields": ["name", "email", "password", "createdAt", "updatedAt"],
                "affected_step": 1,
            }
        ],
        "external_dependencies": [
            {"package": "bcryptjs", "version": "^5.0.0", "purpose": "Password hashing"},
            {
                "package": "jsonwebtoken",
                "version": "^9.0.0",
                "purpose": "JWT token generation",
            },
            {"package": "joi", "version": "^17.0.0", "purpose": "Input validation"},
        ],
        "internal_dependencies": [
            {"module": "User model", "required_by_step": 2},
            {"module": "User repository", "required_by_step": 3},
            {"module": "Auth service", "required_by_step": 4},
            {"module": "Validation middleware", "required_by_step": 5},
        ],
        "story_points": 8,
        "execution_order": [
            "Execute steps sequentially: 1 → 2 → 3 → 4 → 5 → 6 → 7",
            "Within each step, execute sub-steps in order",
            "Test after each sub-step before proceeding",
            "Commit code after each completed sub-step",
        ],
    }

    result = implementor.run(
        implementation_plan=new_project_plan,
        task_description="Initialize new FastAPI project with authentication",
        codebase_path=test_dir,  # Use the test directory we created
        thread_id="new_project_test",
    )

    print(f"New Project Test Result: {result.get('status', 'unknown')}")
    return result


def main():
    """Run all tests."""
    print("🚀 Starting Implementor Agent Tests...\n")

    # Test 2: New project scenario
    result2 = test_implementor_new_project()

    print("\n🏁 All Tests Completed!")
    print(
        f"   Test 2 (New Project): {'✅ PASSED' if result2 and result2.get('status') != 'error' else '❌ FAILED'}"
    )


if __name__ == "__main__":
    main()
