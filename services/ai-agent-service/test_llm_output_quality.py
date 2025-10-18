#!/usr/bin/env python3
"""
Test script để verify LLM output quality sau khi cải tiến prompt engineering.

Kiểm tra:
1. Tất cả required fields được điền
2. Không có trường trống không cần thiết
3. Không có null values
4. Không có empty arrays (trừ khi thực sự trống)
5. JSON output hợp lệ
"""

import json
import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))


def check_field_completeness(data, path=""):
    """Recursively check for empty fields in JSON data."""
    issues = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            # Check for None values
            if value is None:
                issues.append(f"❌ {current_path}: NULL value")

            # Check for empty strings (except for optional fields)
            elif (
                isinstance(value, str)
                and value == ""
                and key not in ["template", "code_template"]
            ):
                issues.append(f"❌ {current_path}: Empty string")

            # Check for empty arrays (except for truly optional fields)
            elif isinstance(value, list) and len(value) == 0:
                optional_empty_arrays = [
                    "alternatives_considered",
                    "error_handling",
                    "dependencies",
                    "files",
                    "external_dependencies",
                    "internal_dependencies",
                ]
                if key not in optional_empty_arrays:
                    issues.append(f"⚠️  {current_path}: Empty array")

            # Recursively check nested objects
            elif isinstance(value, (dict, list)):
                issues.extend(check_field_completeness(value, current_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            issues.extend(check_field_completeness(item, current_path))

    return issues


def validate_implementation_plan(plan_json_str):
    """Validate implementation plan JSON output."""
    print("\n" + "=" * 70)
    print("🔍 VALIDATING IMPLEMENTATION PLAN OUTPUT")
    print("=" * 70)

    try:
        # Parse JSON
        plan = json.loads(plan_json_str)
        print("✅ Valid JSON format")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False

    # Check required top-level fields
    required_fields = [
        "plan_type",
        "task_id",
        "description",
        "complexity_score",
        "complexity_reasoning",
        "approach",
        "implementation_steps",
        "estimated_hours",
        "story_points",
        "requirements",
        "file_changes",
        "infrastructure",
        "risks",
        "assumptions",
        "metadata",
    ]

    print("\n📋 Checking required fields:")
    missing_fields = []
    for field in required_fields:
        if field not in plan:
            print(f"  ❌ Missing: {field}")
            missing_fields.append(field)
        else:
            print(f"  ✅ Present: {field}")

    if missing_fields:
        print(f"\n❌ Missing {len(missing_fields)} required fields")
        return False

    # Check field completeness
    print("\n🔎 Checking field completeness:")
    issues = check_field_completeness(plan)

    if issues:
        print(f"Found {len(issues)} issues:")
        for issue in issues[:20]:  # Show first 20 issues
            print(f"  {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more issues")
    else:
        print("✅ No empty fields found")

    # Check implementation_steps
    print("\n📝 Checking implementation_steps:")
    steps = plan.get("implementation_steps", [])
    if not steps:
        print("  ❌ No implementation steps")
        return False

    print(f"  ✅ {len(steps)} steps found")

    required_step_fields = [
        "step",
        "title",
        "description",
        "files",
        "estimated_hours",
        "complexity",
        "dependencies",
        "blocking",
        "validation",
    ]

    for i, step in enumerate(steps):
        missing = [f for f in required_step_fields if f not in step]
        if missing:
            print(f"  ❌ Step {i + 1} missing: {missing}")
        else:
            print(f"  ✅ Step {i + 1} complete")

    # Check complexity_score
    print("\n📊 Checking complexity_score:")
    complexity = plan.get("complexity_score", 0)
    if 1 <= complexity <= 10:
        print(f"  ✅ Valid complexity score: {complexity}/10")
    else:
        print(f"  ❌ Invalid complexity score: {complexity} (must be 1-10)")
        return False

    # Check story_points
    print("\n🎯 Checking story_points:")
    story_points = plan.get("story_points", 0)
    if 1 <= story_points <= 13:
        print(f"  ✅ Valid story points: {story_points}")
    else:
        print(f"  ❌ Invalid story points: {story_points} (must be 1-13)")
        return False

    # Check estimated_hours
    print("\n⏱️  Checking estimated_hours:")
    hours = plan.get("estimated_hours", 0)
    if hours > 0:
        print(f"  ✅ Valid estimated hours: {hours}")
    else:
        print(f"  ❌ Invalid estimated hours: {hours} (must be > 0)")
        return False

    # Summary
    print("\n" + "=" * 70)
    if not issues and not missing_fields:
        print("✅ PLAN VALIDATION PASSED")
        print("   - All required fields present")
        print("   - No empty fields")
        print("   - Valid complexity score, story points, and hours")
        return True
    else:
        print("❌ PLAN VALIDATION FAILED")
        print(f"   - Missing fields: {len(missing_fields)}")
        print(f"   - Empty/null fields: {len(issues)}")
        return False


def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("🚀 LLM OUTPUT QUALITY TEST")
    print("=" * 70)

    # Example of a good plan (from prompt template)
    good_plan = {
        "plan_type": "simple",
        "task_id": "TSK-042",
        "description": "Add email verification to user registration flow",
        "complexity_score": 4,
        "complexity_reasoning": "Requires 3 file changes, 1 DB migration, follows existing pattern",
        "approach": {
            "strategy": "Extend existing registration flow",
            "pattern": "Follow existing notification pattern",
            "architecture_alignment": "Aligns with service-oriented architecture",
            "alternatives_considered": [],
        },
        "implementation_steps": [
            {
                "step": 1,
                "title": "Create database migration",
                "description": "Add email_verified column",
                "files": ["alembic/versions/add_email_verification.py"],
                "estimated_hours": 1.0,
                "complexity": "low",
                "dependencies": [],
                "blocking": True,
                "validation": "Verify columns exist",
                "error_handling": ["Handle migration conflicts"],
            }
        ],
        "estimated_hours": 8.5,
        "story_points": 3,
        "requirements": {
            "functional_requirements": ["Users must verify email"],
            "acceptance_criteria": ["Given user on registration page..."],
            "business_rules": {"email_verification": "All users must verify"},
            "technical_specs": {"framework": "FastAPI", "database": "PostgreSQL"},
            "constraints": ["Must maintain backward compatibility"],
        },
        "file_changes": {
            "files_to_create": [
                {
                    "path": "app/services/email_verification.py",
                    "reason": "Encapsulate email verification logic",
                    "template": "app/services/notification.py",
                    "estimated_lines": 120,
                    "complexity": "medium",
                }
            ],
            "files_to_modify": [
                {
                    "path": "app/models/user.py",
                    "lines": [15, 20],
                    "changes": "Add email_verified field",
                    "complexity": "low",
                    "risk": "low",
                }
            ],
            "affected_modules": ["app.models", "app.services"],
        },
        "infrastructure": {
            "database_changes": [
                {
                    "type": "add_column",
                    "table": "users",
                    "details": "Add email_verified column",
                    "migration_complexity": "low",
                }
            ],
            "api_endpoints": [
                {
                    "endpoint": "POST /api/v1/auth/verify-email",
                    "method": "POST",
                    "status": "new",
                    "changes": "New endpoint",
                }
            ],
            "external_dependencies": [],
            "internal_dependencies": [
                {
                    "module": "app.services.notification",
                    "reason": "Use existing email sending",
                    "status": "existing",
                }
            ],
        },
        "risks": [
            {
                "risk": "Email sending failures",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Implement retry logic",
            }
        ],
        "assumptions": ["Email service is configured"],
        "metadata": {
            "planner_version": "1.0",
            "created_by": "planner_agent",
            "validation_passed": True,
        },
    }

    # Test with good plan
    print("\n📌 Testing with GOOD plan (from template):")
    result = validate_implementation_plan(json.dumps(good_plan))

    if result:
        print("\n🎉 Good plan validation PASSED")
    else:
        print("\n⚠️  Good plan validation FAILED")

    return result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
