"""
Test Implementor Agent with Test Mode

Test file để verify Implementor Agent functionality với test mode để skip branch creation.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.developer.implementor.agent import ImplementorAgent


def test_implementor_with_test_mode():
    """Test implementor với test mode (skip branch creation)."""

    print("\n🧪 Testing Implementor with Test Mode...")

    implementor = ImplementorAgent(model="gpt-4o")

    # Mock plan for new FastAPI project (nested format)
    test_plan = {
        "task_info": {
            "task_id": "TSK-9640",
            "description": "Implement user authentication system with email verification",
            "complexity_score": 7,
            "plan_type": "complex"
        },
        "requirements": {
            "functional_requirements": [
                "Users can register with an email and password",
                "Email verification is required before account activation",
                "Users can reset their password via email"
            ],
            "technical_specs": {
                "framework": "FastAPI for API endpoints",
                "database": "PostgreSQL database with SQLModel",
                "authentication": "JWT tokens for session management",
                "email": "SMTP for sending verification emails"
            },
            "constraints": [
                "Must maintain backward compatibility",
                "Must follow existing code style and patterns",
                "Must include proper error handling"
            ]
        },
        "implementation": {
            "approach": {
                "strategy": "Develop a comprehensive user authentication system",
                "pattern": "Follow existing patterns in the codebase for services and API endpoints",
                "architecture_alignment": "Aligns with the current microservices architecture"
            }
        },
        "file_changes": {
            "files_to_create": [
                {
                    "path": "app/services/email_service.py",
                    "reason": "To encapsulate email sending functionality for verification and password reset",
                    "template": "Follow the pattern in app/services/auth.py for service classes"
                },
                {
                    "path": "app/api/auth.py",
                    "reason": "API endpoints for user registration, login, and password reset",
                    "template": "Follow FastAPI patterns with proper error handling"
                }
            ],
            "files_to_modify": [
                {
                    "path": "app/models/user.py",
                    "changes": "Add a new column 'is_verified' to track email verification status",
                    "complexity": "medium"
                }
            ]
        },
        "infrastructure": {
            "dependencies": ["fastapi", "sqlmodel", "pydantic", "passlib"],
            "environment_variables": ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"]
        },
        "metadata": {
            "estimated_time": "4-6 hours",
            "risk_level": "medium",
            "testing_requirements": ["Unit tests for services", "Integration tests for API endpoints"]
        }
    }

    try:
        print("🚀 Starting Implementor Agent with Test Mode...")
        print("📊 Executing implementation workflow...")

        # Run implementor với test mode
        result = implementor.run(
            implementation_plan=test_plan,
            task_description="Implement user authentication system with email verification",
            codebase_path=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
            test_mode=True  # Enable test mode to skip branch creation
        )

        print(f"\n📊 Test Result: {result.get('status', 'unknown')}")
        
        if result.get("status") == "success":
            print("✅ Test PASSED - Workflow completed successfully")
            
            # Show what was generated
            if "files_created" in result:
                print(f"📁 Files Created: {len(result['files_created'])}")
                for file_path in result["files_created"]:
                    print(f"   - {file_path}")
                    
            if "files_modified" in result:
                print(f"📝 Files Modified: {len(result['files_modified'])}")
                for file_path in result["files_modified"]:
                    print(f"   - {file_path}")
                    
        else:
            print("❌ Test FAILED")
            if "error_message" in result:
                print(f"   Error: {result['error_message']}")

        return result.get("status") == "success"

    except Exception as e:
        print(f"❌ Implementor workflow failed: {e}")
        return False


def main():
    """Run test with test mode."""
    print("🚀 Testing Implementor Agent with Test Mode...\n")
    
    success = test_implementor_with_test_mode()
    
    print("\n🏁 Test Completed!")
    print(f"   Result: {'✅ PASSED' if success else '❌ FAILED'}")
    
    if success:
        print("\n🎉 Test mode works! Workflow can skip branch creation and continue with code generation!")
    else:
        print("\n💥 Test failed - check implementation")


if __name__ == "__main__":
    main()
