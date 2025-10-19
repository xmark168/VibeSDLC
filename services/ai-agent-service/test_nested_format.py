"""
Test nested format support in Implementor Agent.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.developer.implementor.utils.validators import validate_implementation_plan


def test_nested_format():
    """Test validator with nested format from Planner Agent."""
    
    print("🧪 Testing Nested Format Support...")
    
    # Nested format (from Planner Agent)
    nested_plan = {
        "task_info": {
            "task_id": "TSK-9640",
            "description": "Implement user authentication system with email verification",
            "complexity_score": 7,
            "plan_type": "complex"
        },
        "requirements": {
            "functional_requirements": [
                "Users can register with an email and password",
                "Email verification is required before account activation"
            ],
            "technical_specs": {
                "framework": "FastAPI for API endpoints",
                "database": "PostgreSQL database with SQLModel"
            },
            "constraints": [
                "Must maintain backward compatibility",
                "Must follow existing code style and patterns"
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
                }
            ],
            "files_to_modify": [
                {
                    "path": "app/models/user.py",
                    "changes": "Add a new column 'is_verified' to track email verification status",
                    "complexity": "medium"
                }
            ]
        }
    }
    
    # Flat format (backward compatibility)
    flat_plan = {
        "task_id": "TSK-9640",
        "description": "Implement user authentication system with email verification",
        "files_to_create": [
            {
                "file_path": "app/services/email_service.py",
                "description": "Email service for verification and password reset"
            }
        ],
        "files_to_modify": [
            {
                "file_path": "app/models/user.py",
                "description": "Add email verification field"
            }
        ]
    }
    
    print("\n📋 Testing Nested Format:")
    nested_valid, nested_issues = validate_implementation_plan(nested_plan)
    print(f"   Valid: {nested_valid}")
    if nested_issues:
        print(f"   Issues: {nested_issues}")
    else:
        print("   ✅ No issues found")
    
    print("\n📋 Testing Flat Format (Backward Compatibility):")
    flat_valid, flat_issues = validate_implementation_plan(flat_plan)
    print(f"   Valid: {flat_valid}")
    if flat_issues:
        print(f"   Issues: {flat_issues}")
    else:
        print("   ✅ No issues found")
    
    print(f"\n📊 Results:")
    print(f"   Nested Format: {'✅ PASSED' if nested_valid else '❌ FAILED'}")
    print(f"   Flat Format: {'✅ PASSED' if flat_valid else '❌ FAILED'}")
    
    return nested_valid and flat_valid


def main():
    """Run nested format test."""
    print("🚀 Testing Nested Format Support in Implementor Agent...\n")
    
    success = test_nested_format()
    
    print("\n🏁 Test Completed!")
    print(f"   Overall: {'✅ PASSED' if success else '❌ FAILED'}")
    
    if success:
        print("\n🎉 Implementor Agent now supports both nested and flat formats!")
        print("✅ Ready to receive implementation plans from Planner Agent")
    else:
        print("\n💥 Some tests failed - check validator implementation")


if __name__ == "__main__":
    main()
