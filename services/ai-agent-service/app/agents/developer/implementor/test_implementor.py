"""
Test Implementor Agent

Test file để verify Implementor Agent functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.developer.implementor.agent import ImplementorAgent


def cleanup_test_branch(test_dir: str, branch_name: str):
    """Clean up test branch if it exists."""
    import subprocess

    try:
        # Check if branch exists
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=test_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and branch_name in result.stdout:
            print(f"🧹 Cleaning up existing branch: {branch_name}")

            # Switch to main first
            subprocess.run(
                ["git", "checkout", "main"], cwd=test_dir, capture_output=True
            )

            # Delete the branch
            subprocess.run(
                ["git", "branch", "-D", branch_name], cwd=test_dir, capture_output=True
            )
            print(f"✅ Cleaned up branch: {branch_name}")

    except subprocess.CalledProcessError as e:
        print(f"⚠️ Branch cleanup failed: {e}")


def test_implementor_new_project():
    """Test implementor với new project scenario."""

    print("\n🧪 Testing New Project Scenario...")

    # Create test directory structure
    import os

    test_dir = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
        print(f"📁 Created test directory: {test_dir}")

    # Initialize git repo if needed
    if not os.path.exists(os.path.join(test_dir, ".git")):
        import subprocess

        try:
            subprocess.run(
                ["git", "init"], cwd=test_dir, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=test_dir,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"], cwd=test_dir, check=True
            )
            print(f"🔧 Initialized git repo in {test_dir}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Git init failed: {e}")

    # Clean up any existing test branch
    cleanup_test_branch(test_dir, "feature/tsk-9640")

    implementor = ImplementorAgent(model="gpt-4o")

    # Mock plan for new FastAPI project
    new_project_plan = {
        "task_id": "TSK-9011",
        "description": "Task: Implement user registration functionality\nTask Description: Create user registration API endpo...",
        "complexity_score": 7,
        "plan_type": "complex",
        "functional_requirements": [
            "Create a POST /api/auth/register endpoint that accepts email, password, and confirm_password.",
            "Implement password validation that requires a minimum of 8 characters, including at least one uppercase letter, one lowercase letter, one number, and one special character.",
            "Ensure email validation checks for proper format and uniqueness in the database.",
            "Hash the password using bcrypt before storing it in the database.",
            "Store user data in the database with a created_at timestamp.",
            "Return a JWT token upon successful registration.",
            "Return appropriate error messages for validation failures.",
            "Include comprehensive unit tests for all scenarios related to registration.",
            "Update API documentation with details of the /api/auth/register endpoint.",
        ],
        "steps": [
            {
                "step": 1,
                "title": "Setup and preparation",
                "description": "Initialize development environment and dependencies for user registration.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "1.1",
                        "title": "Install necessary libraries",
                        "description": "Add express, mongoose, bcrypt, jsonwebtoken, and validator libraries to package.json.",
                        "action_type": "setup",
                        "files_affected": ["package.json"],
                        "test": "Run npm install and verify express, mongoose, bcrypt, jsonwebtoken, and validator are installed correctly.",
                    },
                    {
                        "sub_step": "1.2",
                        "title": "Create user model",
                        "description": "Define the user schema with email, password, and created_at fields.",
                        "action_type": "create",
                        "files_affected": ["src/models/user.js"],
                        "test": "Import User model and verify schema structure by creating a test user instance.",
                    },
                    {
                        "sub_step": "1.3",
                        "title": "Setup database connection",
                        "description": "Configure MongoDB connection in app.js.",
                        "action_type": "modify",
                        "files_affected": ["src/app.js"],
                        "test": "Start application and verify successful connection to MongoDB without errors.",
                    },
                ],
                "dependencies": [],
                "estimated_hours": 0.0,
                "complexity": "medium",
            },
            {
                "step": 2,
                "title": "Core implementation",
                "description": "Implement user registration API endpoint and validation logic.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "2.1",
                        "title": "Create registration route",
                        "description": "Setup POST /api/auth/register route with Express router.",
                        "action_type": "create",
                        "files_affected": ["src/routes/auth.js"],
                        "test": "Send POST request to /api/auth/register and verify route is accessible (404 → 400/500).",
                    },
                    {
                        "sub_step": "2.2",
                        "title": "Implement registration controller logic",
                        "description": "Create controller to handle user registration, including validation and password hashing.",
                        "action_type": "create",
                        "files_affected": ["src/services/authService.js"],
                        "test": "Call registration controller with valid data and verify user is created in the database.",
                    },
                    {
                        "sub_step": "2.3",
                        "title": "Add request validation middleware",
                        "description": "Validate email format, password strength, and confirm password match.",
                        "action_type": "create",
                        "files_affected": ["src/middleware/validation.js"],
                        "test": "Send invalid registration request and verify appropriate validation error messages.",
                    },
                    {
                        "sub_step": "2.4",
                        "title": "Hash password before storing",
                        "description": "Use bcrypt to hash the password before saving user data to the database.",
                        "action_type": "modify",
                        "files_affected": ["src/services/authService.js"],
                        "test": "Verify that the password stored in the database is hashed and not plain text.",
                    },
                    {
                        "sub_step": "2.5",
                        "title": "Generate JWT token on successful registration",
                        "description": "Return a JWT token upon successful registration.",
                        "action_type": "modify",
                        "files_affected": ["src/services/authService.js"],
                        "test": "Verify that a valid JWT token is returned upon successful registration.",
                    },
                ],
                "dependencies": [],
                "estimated_hours": 0.0,
                "complexity": "medium",
            },
            {
                "step": 3,
                "title": "Integration and testing",
                "description": "Integrate components and validate functionality through unit tests.",
                "category": "backend",
                "sub_steps": [
                    {
                        "sub_step": "3.1",
                        "title": "Write unit tests for registration",
                        "description": "Implement unit tests for all scenarios related to user registration.",
                        "action_type": "create",
                        "files_affected": ["src/tests/auth.test.js"],
                        "test": "Run test suite and verify all registration tests pass successfully.",
                    },
                    {
                        "sub_step": "3.2",
                        "title": "Update API documentation",
                        "description": "Document the /api/auth/register endpoint with request and response examples.",
                        "action_type": "modify",
                        "files_affected": ["docs/api.md"],
                        "test": "Verify that the documentation accurately reflects the registration endpoint and its requirements.",
                    },
                ],
                "dependencies": [],
                "estimated_hours": 0.0,
                "complexity": "medium",
            },
        ],
        "database_changes": [
            {
                "change": "Add users collection",
                "fields": ["email", "password", "created_at"],
                "affected_step": 1,
            }
        ],
        "external_dependencies": [
            {
                "package": "jsonwebtoken",
                "version": "^9.0.0",
                "purpose": "JWT token generation",
            },
            {"package": "bcrypt", "version": "^5.1.0", "purpose": "Password hashing"},
            {
                "package": "validator",
                "version": "^13.6.0",
                "purpose": "Input validation",
            },
        ],
        "internal_dependencies": [
            {"module": "User model", "required_by_step": 2},
            {"module": "Validation middleware", "required_by_step": 2},
        ],
        "total_estimated_hours": 5.5,
        "story_points": 8,
        "execution_order": [
            "Execute steps sequentially: 1 → 2 → 3",
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
