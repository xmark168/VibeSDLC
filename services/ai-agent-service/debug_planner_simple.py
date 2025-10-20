"""
Simple debug script to test Planner Agent output without full dependencies.
"""

import json
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def simulate_planner_agent_call():
    """Simulate a planner agent call and show expected output structure."""
    
    print("🔍 SIMULATING PLANNER AGENT OUTPUT")
    print("="*80)
    
    # This is what we expect from a successful planner agent call
    expected_planner_result = {
        "success": True,
        "final_plan": {
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
                        "changes": "Add bcrypt and python-jose dependencies for authentication",
                        "complexity": "low",
                        "risk": "low"
                    }
                ],
                "affected_modules": ["app.api", "app.models", "app.services", "app.schemas"]
            },
            "implementation": {
                "approach": {
                    "strategy": "Create comprehensive authentication system",
                    "rationale": "Implement secure user registration with proper validation"
                },
                "steps": [
                    {
                        "step": 1,
                        "title": "Create User model",
                        "description": "Define User model with authentication fields"
                    },
                    {
                        "step": 2,
                        "title": "Create authentication service",
                        "description": "Implement password hashing and validation logic"
                    },
                    {
                        "step": 3,
                        "title": "Create API schemas",
                        "description": "Define Pydantic schemas for requests/responses"
                    },
                    {
                        "step": 4,
                        "title": "Create authentication routes",
                        "description": "Implement registration and login endpoints"
                    },
                    {
                        "step": 5,
                        "title": "Update main app",
                        "description": "Register authentication router"
                    },
                    {
                        "step": 6,
                        "title": "Add dependencies",
                        "description": "Update requirements.txt with auth dependencies"
                    },
                    {
                        "step": 7,
                        "title": "Create tests",
                        "description": "Implement comprehensive unit tests"
                    }
                ]
            },
            "infrastructure": {
                "database_changes": [
                    {
                        "type": "table",
                        "name": "users",
                        "operation": "create",
                        "fields": ["id", "email", "password_hash", "created_at", "updated_at"]
                    }
                ],
                "dependencies": [
                    "bcrypt",
                    "python-jose[cryptography]",
                    "passlib[bcrypt]"
                ]
            }
        },
        "execution_time": 15.2,
        "tokens_used": 1250
    }
    
    # Simulate the debug output that would be printed
    print_planner_debug(expected_planner_result, "TASK-001")
    
    # Also show what happens with empty file operations (the problem case)
    print("\n" + "="*80)
    print("🚨 PROBLEM CASE: Empty file operations")
    print("="*80)
    
    empty_result = {
        "success": True,
        "final_plan": {
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
    }
    
    print_planner_debug(empty_result, "TASK-001")


def print_planner_debug(result, task_id):
    """Print the same debug output that would be shown in the actual agent."""
    
    if result.get("success", False):
        print("\n🔍 PLANNER AGENT STATE JSON DEBUG")
        print("="*80)
        
        # Print final plan structure
        final_plan = result.get("final_plan", {})
        print(f"📋 Final Plan Keys: {list(final_plan.keys())}")
        
        # Print task info
        if "task_info" in final_plan:
            task_info = final_plan["task_info"]
            print(f"\n📝 Task Info:")
            print(f"  - task_id: {task_info.get('task_id', 'MISSING')}")
            print(f"  - description: {task_info.get('description', 'MISSING')[:100]}...")
            print(f"  - complexity_score: {task_info.get('complexity_score', 'MISSING')}")
        
        # Print file changes (most important for debugging)
        if "file_changes" in final_plan:
            file_changes = final_plan["file_changes"]
            files_to_create = file_changes.get("files_to_create", [])
            files_to_modify = file_changes.get("files_to_modify", [])
            
            print(f"\n📁 File Changes:")
            print(f"  - files_to_create: {len(files_to_create)} files")
            for i, file_info in enumerate(files_to_create):
                print(f"    [{i+1}] {file_info.get('path', 'NO_PATH')}: {file_info.get('reason', 'NO_REASON')}")
            
            print(f"  - files_to_modify: {len(files_to_modify)} files")
            for i, file_info in enumerate(files_to_modify):
                print(f"    [{i+1}] {file_info.get('path', 'NO_PATH')}: {file_info.get('changes', 'NO_CHANGES')}")
            
            # Check if empty (this is the problem we're debugging)
            if len(files_to_create) == 0 and len(files_to_modify) == 0:
                print("❌ PROBLEM DETECTED: No file operations specified!")
                print("This will cause Implementor Agent validation to fail.")
            else:
                print("✅ File operations found - should pass validation")
        
        # Save full state to JSON file for detailed inspection
        debug_file = f"debug_planner_state_{task_id}.json"
        try:
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n💾 Full planner state saved to: {debug_file}")
        except Exception as save_error:
            print(f"⚠️ Could not save debug file: {save_error}")
        
        print("="*80 + "\n")


def show_implementor_validation_logic():
    """Show how Implementor Agent validates the plan."""
    
    print("🔧 IMPLEMENTOR AGENT VALIDATION LOGIC")
    print("="*80)
    
    print("The Implementor Agent validates plans using this logic:")
    print("""
def validate_implementation_plan(implementation_plan):
    issues = []
    
    # Check required fields
    if "task_info" in implementation_plan:
        task_info = implementation_plan["task_info"]
        task_id = task_info.get("task_id", "")
        description = task_info.get("description", "")
    else:
        task_id = implementation_plan.get("task_id", "")
        description = implementation_plan.get("description", "")
    
    if not task_id:
        issues.append("Missing required field: task_id")
    if not description:
        issues.append("Missing required field: description")
    
    # Validate file operations - support both nested and flat formats
    if "file_changes" in implementation_plan:
        file_changes = implementation_plan["file_changes"]
        files_to_create = file_changes.get("files_to_create", [])
        files_to_modify = file_changes.get("files_to_modify", [])
    else:
        files_to_create = implementation_plan.get("files_to_create", [])
        files_to_modify = implementation_plan.get("files_to_modify", [])
    
    # THIS IS THE KEY CHECK THAT FAILS:
    if not files_to_create and not files_to_modify:
        issues.append("No file operations specified - nothing to implement")
    
    return len(issues) == 0, issues
    """)
    
    print("\n🎯 KEY INSIGHT:")
    print("If both files_to_create and files_to_modify are empty arrays,")
    print("the validation fails with: 'No file operations specified - nothing to implement'")
    print("\nThis is exactly the error you're seeing!")


def main():
    """Run the debug simulation."""
    
    print("🚀 PLANNER AGENT DEBUG SIMULATION")
    print("="*80)
    print("This simulates what the planner agent output should look like")
    print("and shows the debug information that will be printed.\n")
    
    # Show expected vs problem scenarios
    simulate_planner_agent_call()
    
    # Show validation logic
    show_implementor_validation_logic()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Run the actual test to see if Planner Agent generates empty file operations")
    print("2. If it does, the fallback logic we added should kick in")
    print("3. Check the debug JSON files to see the actual planner output")
    print("4. Compare with the expected structure shown above")


if __name__ == "__main__":
    main()
