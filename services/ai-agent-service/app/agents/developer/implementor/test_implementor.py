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
        "task_info": {
            "task_id": "TSK-9640",
            "description": "\n    Implement user authentication system with email verification.\n\n    Requirements:\n    - Users ca...",
            "complexity_score": 7,
            "plan_type": "complex",
        },
        "requirements": {
            "functional_requirements": [
                "Users can register with an email and password.",
                "Email verification is required before account activation.",
                "Users can log in with email and password only after email verification.",
                "Password reset functionality must be available.",
            ],
            "acceptance_criteria": [
                "Given a user registers with email and password, when they submit the registration form, then the registration endpoint accepts email, password, and confirm_password.",
                "Given a successful registration, when the registration is complete, then a verification email is sent automatically to the user's email address.",
                "Given a user attempts to log in, when their email is not verified, then they cannot log in until email verification is completed.",
                "Given a user requests a password reset, when they submit their email, then a secure reset link is sent to their email address.",
                "Given any API endpoint interaction, when an error occurs, then all endpoints return appropriate error messages.",
            ],
            "business_rules": {
                "Email Verification": "Users must verify their email address before they can log in. If a user tries to log in without verifying their email, an error message must be displayed."
            },
            "technical_specs": {
                "framework": "FastAPI for API endpoints.",
                "database": "PostgreSQL database with SQLModel.",
                "apis": [
                    "Email service integration (SMTP or SendGrid) for sending verification and reset emails."
                ],
            },
            "constraints": [
                "Must maintain backward compatibility",
                "Must follow existing code style and patterns",
                "Must include appropriate error handling",
            ],
        },
        "implementation": {
            "approach": {
                "strategy": "Develop a comprehensive user authentication system that includes email verification and password reset functionalities.",
                "pattern": "Follow existing patterns in the codebase for services and API endpoints.",
                "architecture_alignment": "Aligns with the current microservices architecture by encapsulating email functionalities in a dedicated service.",
            },
            "steps": [
                {
                    "step": 1,
                    "title": "Create database migration",
                    "description": "Add 'is_verified' column to the users table to track email verification status.",
                    "action": "Create a migration script to alter the users table.",
                    "files": ["migrations/add_new_feature_tables.py"],
                    "estimated_hours": 1.5,
                    "complexity": "medium",
                    "dependencies": [],
                    "blocking": "true",
                    "validation": "Confirm the 'is_verified' column exists in the database schema.",
                    "error_handling": [
                        "Handle migration conflicts",
                        "Rollback on failure",
                    ],
                    "code_template": "ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE",
                },
                {
                    "step": 2,
                    "title": "Update User model",
                    "description": "Modify the User model to include the new 'is_verified' field.",
                    "action": "Update app/models/user.py to reflect the new column.",
                    "files": ["app/models/user.py"],
                    "estimated_hours": 1.0,
                    "complexity": "medium",
                    "dependencies": [1],
                    "blocking": "true",
                    "validation": "Run unit tests to ensure the User model behaves as expected.",
                    "error_handling": ["Handle field validation errors"],
                    "code_template": "is_verified: bool = Field(default=False)",
                },
                {
                    "step": 3,
                    "title": "Implement email service",
                    "description": "Create a service for handling email sending for verification and password resets.",
                    "action": "Develop app/services/email_service.py to encapsulate email functionalities.",
                    "files": ["app/services/email_service.py"],
                    "estimated_hours": 2.5,
                    "complexity": "high",
                    "dependencies": [2],
                    "blocking": "true",
                    "validation": "Unit tests for email sending functionalities must pass.",
                    "error_handling": [
                        "Handle email sending failures",
                        "Handle invalid email addresses",
                    ],
                    "code_template": "def send_verification_email(user_email: str, token: str): ...",
                },
                {
                    "step": 4,
                    "title": "Add API endpoints for authentication",
                    "description": "Implement endpoints for user registration, email verification, and password reset.",
                    "action": "Modify app/api/v1/endpoints/auth.py to include new endpoints.",
                    "files": ["app/api/v1/endpoints/auth.py"],
                    "estimated_hours": 2.0,
                    "complexity": "medium",
                    "dependencies": [3],
                    "blocking": "false",
                    "validation": "Integration tests for new endpoints must be executed successfully.",
                    "error_handling": [
                        "Handle missing parameters",
                        "Handle user not found errors",
                    ],
                    "code_template": "@router.post('/register')",
                },
                {
                    "step": 5,
                    "title": "Update schemas for new functionalities",
                    "description": "Add schemas for email verification and password reset requests.",
                    "action": "Modify app/schemas/user.py to include new request schemas.",
                    "files": ["app/schemas/user.py"],
                    "estimated_hours": 1.0,
                    "complexity": "low",
                    "dependencies": [],
                    "blocking": "false",
                    "validation": "Ensure new schemas are validated correctly in tests.",
                    "error_handling": ["Handle schema validation errors"],
                    "code_template": "class EmailVerificationRequest(BaseModel): ...",
                },
                {
                    "step": 6,
                    "title": "Implement custom exceptions",
                    "description": "Add exceptions for handling email verification and password reset errors.",
                    "action": "Update app/core/exceptions.py to define new exception classes.",
                    "files": ["app/core/exceptions.py"],
                    "estimated_hours": 1.0,
                    "complexity": "low",
                    "dependencies": [],
                    "blocking": "false",
                    "validation": "Ensure exceptions are raised and handled correctly in the application.",
                    "error_handling": ["Handle unhandled exceptions gracefully"],
                    "code_template": "class EmailVerificationError(Exception): ...",
                },
            ],
            "execution_order": [
                {
                    "step": 1,
                    "action": "Create database migration",
                    "reason": "Database schema changes must be applied first",
                    "blocking": "true",
                    "depends_on": [],
                    "files": ["migrations/add_new_feature_tables.py"],
                },
                {
                    "step": 2,
                    "action": "Update data models",
                    "reason": "Services depend on updated models",
                    "blocking": "true",
                    "depends_on": [1],
                    "files": ["app/models/user.py"],
                },
                {
                    "step": 3,
                    "action": "Implement service layer",
                    "reason": "Business logic implementation",
                    "blocking": "true",
                    "depends_on": [2],
                    "files": ["app/services/email_service.py"],
                },
                {
                    "step": 4,
                    "action": "Add API endpoints",
                    "reason": "External interface implementation",
                    "blocking": "false",
                    "depends_on": [3],
                    "files": ["app/api/v1/endpoints/auth.py"],
                },
            ],
            "parallel_opportunities": [],
            "subtasks": [
                {
                    "subtask_id": "SUB-001",
                    "title": "Create database migration",
                    "description": "Add 'is_verified' column to the users table to track email verification status.",
                    "estimated_hours": 1.5,
                    "priority": "high",
                    "dependencies": [],
                },
                {
                    "subtask_id": "SUB-002",
                    "title": "Update User model",
                    "description": "Modify the User model to include the new 'is_verified' field.",
                    "estimated_hours": 1.0,
                    "priority": "high",
                    "dependencies": [1],
                },
                {
                    "subtask_id": "SUB-003",
                    "title": "Implement email service",
                    "description": "Create a service for handling email sending for verification and password resets.",
                    "estimated_hours": 2.5,
                    "priority": "high",
                    "dependencies": [2],
                },
                {
                    "subtask_id": "SUB-004",
                    "title": "Add API endpoints for authentication",
                    "description": "Implement endpoints for user registration, email verification, and password reset.",
                    "estimated_hours": 2.0,
                    "priority": "medium",
                    "dependencies": [3],
                },
                {
                    "subtask_id": "SUB-005",
                    "title": "Update schemas for new functionalities",
                    "description": "Add schemas for email verification and password reset requests.",
                    "estimated_hours": 1.0,
                    "priority": "medium",
                    "dependencies": [],
                },
                {
                    "subtask_id": "SUB-006",
                    "title": "Implement custom exceptions",
                    "description": "Add exceptions for handling email verification and password reset errors.",
                    "estimated_hours": 1.0,
                    "priority": "medium",
                    "dependencies": [],
                },
            ],
            "execution_strategy": {
                "phases": [
                    {
                        "phase": 1,
                        "name": "Foundation",
                        "subtasks": ["SUB-001", "SUB-002"],
                        "blocking": "true",
                    },
                    {
                        "phase": 2,
                        "name": "Implementation",
                        "subtasks": ["SUB-003", "SUB-004"],
                        "blocking": "true",
                    },
                    {
                        "phase": 3,
                        "name": "Integration",
                        "subtasks": ["SUB-005", "SUB-006"],
                        "blocking": "false",
                    },
                ]
            },
        },
        "file_changes": {
            "files_to_create": [
                {
                    "path": "app/api/v1/endpoints/email_verification.py",
                    "reason": "To handle email verification logic and endpoints.",
                    "template": "Follow the pattern in app/api/v1/endpoints/auth.py for creating new endpoints.",
                },
                {
                    "path": "app/services/email_service.py",
                    "reason": "To encapsulate email sending functionality for verification and password reset.",
                    "template": "Follow the pattern in app/services/auth.py for service classes.",
                },
            ],
            "files_to_modify": [
                {
                    "path": "app/models/user.py",
                    "lines": [15, "20-25"],
                    "changes": "Add a new column 'is_verified' to track email verification status.",
                    "complexity": "medium",
                    "risk": "low",
                },
                {
                    "path": "app/schemas/user.py",
                    "lines": [50, "60-70"],
                    "changes": "Add schemas for email verification and password reset requests.",
                    "complexity": "low",
                    "risk": "low",
                },
                {
                    "path": "app/services/auth.py",
                    "lines": [10, "30-50"],
                    "changes": "Implement methods for sending verification emails and handling password resets.",
                    "complexity": "high",
                    "risk": "medium",
                },
                {
                    "path": "app/api/v1/endpoints/auth.py",
                    "lines": [10, "20-40"],
                    "changes": "Add new endpoints for email verification and password reset.",
                    "complexity": "medium",
                    "risk": "medium",
                },
                {
                    "path": "app/core/exceptions.py",
                    "lines": [15, "30-35"],
                    "changes": "Add custom exceptions for email verification and password reset errors.",
                    "complexity": "low",
                    "risk": "low",
                },
            ],
            "affected_modules": [],
        },
        "infrastructure": {
            "database_changes": [
                {
                    "type": "add_column",
                    "table": "users",
                    "details": "Add 'is_verified' boolean column to track email verification status.",
                    "migration_complexity": "medium",
                }
            ],
            "api_endpoints": [],
            "external_dependencies": [],
            "internal_dependencies": [],
        },
        "metadata": {
            "planner_version": "1.0",
            "planning_iterations": 3,
            "validation_passed": "false",
            "created_by": "planner_subagent",
        },
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
