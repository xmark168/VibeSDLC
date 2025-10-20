"""
Debug Implementation Plan Issue

Simulate và debug vấn đề "No file operations specified" trong Implementor Agent.
"""

import json

def simulate_planner_output_scenarios():
    """Simulate different planner output scenarios."""
    
    print("🧪 Simulating Planner Agent Output Scenarios\n")
    
    # Scenario 1: Empty file operations (PROBLEM CASE)
    empty_plan = {
        "task_info": {
            "task_id": "TASK-001",
            "description": "Implement user registration functionality",
            "complexity_score": 5,
            "plan_type": "simple"
        },
        "file_changes": {
            "files_to_create": [],  # EMPTY!
            "files_to_modify": [],  # EMPTY!
            "affected_modules": []
        },
        "implementation": {
            "approach": {"strategy": "Create new registration endpoint"},
            "steps": [{"step": 1, "title": "Create registration endpoint"}]
        }
    }
    
    # Scenario 2: Valid file operations (WORKING CASE)
    valid_plan = {
        "task_info": {
            "task_id": "TASK-001",
            "description": "Implement user registration functionality",
            "complexity_score": 5,
            "plan_type": "simple"
        },
        "file_changes": {
            "files_to_create": [
                {
                    "path": "app/api/routes/auth.py",
                    "reason": "Create authentication endpoints",
                    "template": "app/api/routes/users.py",
                    "estimated_lines": 150,
                    "complexity": "medium"
                },
                {
                    "path": "app/models/user.py", 
                    "reason": "Create User model with authentication fields",
                    "template": "",
                    "estimated_lines": 80,
                    "complexity": "low"
                }
            ],
            "files_to_modify": [
                {
                    "path": "app/main.py",
                    "lines": [25, 30],
                    "changes": "Add authentication router to main app",
                    "complexity": "low",
                    "risk": "low"
                }
            ],
            "affected_modules": ["app.api", "app.models"]
        },
        "implementation": {
            "approach": {"strategy": "Create new registration endpoint"},
            "steps": [{"step": 1, "title": "Create registration endpoint"}]
        }
    }
    
    # Scenario 3: Wrong field names (FIELD MAPPING ISSUE)
    wrong_fields_plan = {
        "task_info": {
            "task_id": "TASK-001",
            "description": "Implement user registration functionality"
        },
        "file_changes": {
            "files_to_create": [
                {
                    "file_path": "app/api/routes/auth.py",  # Should be "path"
                    "description": "Create authentication endpoints"  # Should be "reason"
                }
            ],
            "files_to_modify": [
                {
                    "file_path": "app/main.py",  # Should be "path"
                    "description": "Add authentication router"  # Should be "changes"
                }
            ]
        }
    }
    
    return {
        "empty_plan": empty_plan,
        "valid_plan": valid_plan,
        "wrong_fields_plan": wrong_fields_plan
    }


def test_implementor_validation_logic(plan, scenario_name):
    """Test implementor validation logic với different scenarios."""
    
    print(f"\n🧪 Testing scenario: {scenario_name}")
    
    # Simulate validation logic from validators.py
    issues = []
    
    # Check required fields - support both nested and flat formats
    if "task_info" in plan:
        task_info = plan["task_info"]
        task_id = task_info.get("task_id", "")
        description = task_info.get("description", "")
    else:
        task_id = plan.get("task_id", "")
        description = plan.get("description", "")
    
    if not task_id:
        issues.append("Missing required field: task_id")
    if not description:
        issues.append("Missing required field: description")
    
    # Validate file operations - support both nested and flat formats
    if "file_changes" in plan:
        file_changes = plan["file_changes"]
        files_to_create = file_changes.get("files_to_create", [])
        files_to_modify = file_changes.get("files_to_modify", [])
    else:
        files_to_create = plan.get("files_to_create", [])
        files_to_modify = plan.get("files_to_modify", [])
    
    if not files_to_create and not files_to_modify:
        issues.append("No file operations specified - nothing to implement")
    
    # Validate file specs
    for i, file_spec in enumerate(files_to_create):
        file_path = file_spec.get("file_path") or file_spec.get("path", "")
        if not file_path:
            issues.append(f"File creation #{i}: missing file_path or path")
    
    for i, file_spec in enumerate(files_to_modify):
        file_path = file_spec.get("file_path") or file_spec.get("path", "")
        if not file_path:
            issues.append(f"File modification #{i}: missing file_path or path")
    
    is_valid = len(issues) == 0
    
    print(f"✅ Validation result: {is_valid}")
    if issues:
        print("❌ Validation issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ No validation issues")
    
    return is_valid, issues


def analyze_root_causes():
    """Analyze possible root causes của empty file operations."""
    
    print("\n🔍 ROOT CAUSE ANALYSIS:")
    print("\nPossible reasons why Planner Agent generates empty file operations:")
    
    print("\n1. 📝 LLM PROMPT ISSUES:")
    print("   - Codebase analysis prompt không clear về file operations")
    print("   - LLM không hiểu authentication task requirements")
    print("   - Prompt không có enough examples cho file creation/modification")
    
    print("\n2. 🏗️ CODEBASE ANALYSIS ISSUES:")
    print("   - Codebase path không tồn tại hoặc empty")
    print("   - Codebase analyzer không detect được existing structure")
    print("   - Demo codebase không có enough context cho authentication")
    
    print("\n3. 🤖 LLM RESPONSE PARSING ISSUES:")
    print("   - LLM response không phải valid JSON")
    print("   - JSON parsing failed, fallback to empty arrays")
    print("   - LLM generate wrong JSON structure")
    
    print("\n4. 📋 TASK DESCRIPTION ISSUES:")
    print("   - Task description quá abstract, không specific về files")
    print("   - Acceptance criteria không mention specific file changes")
    print("   - Missing technical implementation details")


def suggest_fixes():
    """Suggest fixes cho empty file operations issue."""
    
    print("\n💡 SUGGESTED FIXES:")
    
    print("\n1. 🔧 IMMEDIATE FIX - Add fallback file operations:")
    print("   - Modify analyze_codebase node để add default file operations")
    print("   - Nếu LLM không generate files, create reasonable defaults")
    print("   - Based on task type (authentication) → predict common files")
    
    print("\n2. 🎯 IMPROVE PROMPTS:")
    print("   - Add specific examples cho authentication tasks")
    print("   - Make codebase analysis prompt more explicit về file operations")
    print("   - Add validation trong prompt để ensure file operations")
    
    print("\n3. 🏗️ ENHANCE CODEBASE ANALYSIS:")
    print("   - Ensure demo codebase has realistic structure")
    print("   - Add more context về existing authentication patterns")
    print("   - Improve codebase analyzer để detect framework patterns")
    
    print("\n4. 🛡️ ADD VALIDATION & RETRY:")
    print("   - Add validation trong analyze_codebase node")
    print("   - Retry LLM call nếu no file operations generated")
    print("   - Add human-readable error messages")


def create_fallback_implementation():
    """Create fallback implementation cho authentication tasks."""
    
    print("\n🔧 FALLBACK IMPLEMENTATION:")
    
    fallback_auth_files = {
        "files_to_create": [
            {
                "path": "app/api/routes/auth.py",
                "reason": "Authentication endpoints for registration and login",
                "template": "",
                "estimated_lines": 200,
                "complexity": "medium"
            },
            {
                "path": "app/models/user.py",
                "reason": "User model with authentication fields",
                "template": "",
                "estimated_lines": 100,
                "complexity": "low"
            },
            {
                "path": "app/services/auth_service.py",
                "reason": "Authentication business logic and password hashing",
                "template": "",
                "estimated_lines": 150,
                "complexity": "medium"
            },
            {
                "path": "app/schemas/auth.py",
                "reason": "Pydantic schemas for authentication requests/responses",
                "template": "",
                "estimated_lines": 80,
                "complexity": "low"
            },
            {
                "path": "tests/test_auth.py",
                "reason": "Unit tests for authentication functionality",
                "template": "",
                "estimated_lines": 300,
                "complexity": "medium"
            }
        ],
        "files_to_modify": [
            {
                "path": "app/main.py",
                "lines": [20, 25],
                "changes": "Add authentication router to FastAPI app",
                "complexity": "low",
                "risk": "low"
            },
            {
                "path": "requirements.txt",
                "lines": [-1],
                "changes": "Add bcrypt and python-jose dependencies",
                "complexity": "low",
                "risk": "low"
            }
        ]
    }
    
    print("📁 Fallback files for authentication tasks:")
    for file_info in fallback_auth_files["files_to_create"]:
        print(f"  CREATE: {file_info['path']} - {file_info['reason']}")
    
    for file_info in fallback_auth_files["files_to_modify"]:
        print(f"  MODIFY: {file_info['path']} - {file_info['changes']}")
    
    return fallback_auth_files


def main():
    """Run debug analysis."""
    
    print("🚀 Debug Implementation Plan Issue\n")
    
    # Simulate scenarios
    scenarios = simulate_planner_output_scenarios()
    
    # Test each scenario
    for scenario_name, plan in scenarios.items():
        test_implementor_validation_logic(plan, scenario_name)
    
    # Analyze root causes
    analyze_root_causes()
    
    # Suggest fixes
    suggest_fixes()
    
    # Create fallback
    fallback_files = create_fallback_implementation()
    
    print("\n🎯 CONCLUSION:")
    print("The issue is likely that Planner Agent generates empty file operations.")
    print("This causes Implementor Agent validation to fail with:")
    print("'Invalid implementation plan: No file operations specified - nothing to implement'")
    print("\nNext steps:")
    print("1. Add fallback file operations trong analyze_codebase node")
    print("2. Improve LLM prompts với specific examples")
    print("3. Add validation và retry logic")
    print("4. Enhance demo codebase structure")


if __name__ == "__main__":
    main()
