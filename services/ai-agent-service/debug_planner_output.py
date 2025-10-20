"""
Debug Planner Agent Output

Test Planner Agent với authentication tasks để xem implementation plan structure.
"""

import json
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_planner_with_auth_task():
    """Test Planner Agent với user registration task."""
    
    print("🧪 Testing Planner Agent with User Registration Task...")
    
    try:
        from app.agents.developer.planner.agent import PlannerAgent
        
        # Create planner agent
        planner = PlannerAgent(
            model="gpt-4o-mini",  # Use cheaper model for testing
            session_id="debug_session",
            user_id="debug_user"
        )
        
        # Test task description (same as in test_developer_agent.py)
        task_description = """
        **Task ID**: TASK-001
        **Title**: Implement user registration functionality
        **Description**: Create user registration API endpoint with validation, password hashing, and email verification
        **Task Type**: Development
        
        **Acceptance Criteria**:
        - POST /api/auth/register endpoint accepts email, password, and confirm_password
        - Password validation includes minimum 8 characters, uppercase, lowercase, number, special character
        - Email validation ensures proper format and uniqueness
        - Password is hashed using bcrypt before storing in database
        - User data is stored in database with created_at timestamp
        - Returns JWT token upon successful registration
        - Returns appropriate error messages for validation failures
        - Includes comprehensive unit tests for all scenarios
        - API documentation is updated with endpoint details
        
        **Parent Context**: 
        Epic: User Authentication System - Implement comprehensive user authentication system with registration, login, and security features
        """
        
        # Run planner
        print("🚀 Running Planner Agent...")
        result = planner.run(
            task_description=task_description,
            codebase_context="FastAPI application with PostgreSQL database",
            codebase_path=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
            thread_id="debug_planner_thread"
        )
        
        print(f"✅ Planner execution result: {result['success']}")
        
        if result["success"]:
            print(f"📋 Task ID: {result['task_id']}")
            print(f"📊 Complexity: {result['complexity_score']}/10")
            print(f"⏱️  Estimated: {result['estimated_hours']} hours")
            print(f"✅ Ready: {result['ready_for_implementation']}")
            
            # Debug final_plan structure
            final_plan = result.get("final_plan", {})
            print(f"\n🔍 FINAL PLAN STRUCTURE:")
            print(f"Keys: {list(final_plan.keys())}")
            
            # Check task_info
            if "task_info" in final_plan:
                task_info = final_plan["task_info"]
                print(f"\n📋 TASK INFO:")
                print(f"- task_id: {task_info.get('task_id', 'MISSING')}")
                print(f"- description: {task_info.get('description', 'MISSING')[:100]}...")
                print(f"- complexity_score: {task_info.get('complexity_score', 'MISSING')}")
            else:
                print("❌ MISSING: task_info")
            
            # Check file_changes
            if "file_changes" in final_plan:
                file_changes = final_plan["file_changes"]
                print(f"\n📁 FILE CHANGES:")
                
                files_to_create = file_changes.get("files_to_create", [])
                files_to_modify = file_changes.get("files_to_modify", [])
                
                print(f"- files_to_create: {len(files_to_create)} files")
                for i, file_info in enumerate(files_to_create[:3]):  # Show first 3
                    print(f"  [{i+1}] {file_info}")
                
                print(f"- files_to_modify: {len(files_to_modify)} files")
                for i, file_info in enumerate(files_to_modify[:3]):  # Show first 3
                    print(f"  [{i+1}] {file_info}")
                
                if len(files_to_create) == 0 and len(files_to_modify) == 0:
                    print("❌ PROBLEM: No file operations specified!")
                    print("This is why Implementor Agent fails validation.")
                else:
                    print("✅ File operations found")
            else:
                print("❌ MISSING: file_changes")
            
            # Save full plan to file for inspection
            debug_file = "debug_planner_output.json"
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(final_plan, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Full plan saved to: {debug_file}")
            
            return final_plan
            
        else:
            print(f"❌ Planner failed: {result.get('error', 'Unknown error')}")
            return None
            
    except ImportError as e:
        print(f"⚠️  Could not test planner (missing dependencies): {e}")
        return None
    except Exception as e:
        print(f"❌ Planner test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_implementor_validation(final_plan):
    """Test Implementor validation logic với planner output."""
    
    if not final_plan:
        print("⚠️  No final_plan to test")
        return
    
    print("\n🧪 Testing Implementor validation logic...")
    
    try:
        from app.agents.developer.implementor.utils.validators import validate_implementation_plan
        
        # Test validation
        is_valid, issues = validate_implementation_plan(final_plan)
        
        print(f"✅ Validation result: {is_valid}")
        if issues:
            print("❌ Validation issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ No validation issues")
            
        return is_valid, issues
        
    except ImportError as e:
        print(f"⚠️  Could not test validation (missing dependencies): {e}")
        return None, []
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, []


def analyze_field_mapping():
    """Analyze field mapping between Planner output và Implementor input."""
    
    print("\n🔍 FIELD MAPPING ANALYSIS:")
    print("Planner Agent generates:")
    print("  final_plan.file_changes.files_to_create[].path")
    print("  final_plan.file_changes.files_to_create[].reason")
    print("  final_plan.file_changes.files_to_modify[].path")
    print("  final_plan.file_changes.files_to_modify[].changes")
    
    print("\nImplementor Agent expects:")
    print("  implementation_plan.file_changes.files_to_create[].file_path (or .path)")
    print("  implementation_plan.file_changes.files_to_create[].description (or .reason)")
    print("  implementation_plan.file_changes.files_to_modify[].file_path (or .path)")
    print("  implementation_plan.file_changes.files_to_modify[].description (or .changes)")
    
    print("\n💡 Field mapping should work with fallbacks:")
    print("  file_path = file_info.get('file_path') or file_info.get('path', '')")
    print("  description = file_info.get('description') or file_info.get('reason', '')")


def main():
    """Run debug analysis."""
    
    print("🚀 Debug Planner Agent Output for Authentication Tasks\n")
    
    # Test planner
    final_plan = test_planner_with_auth_task()
    
    # Test implementor validation
    if final_plan:
        test_implementor_validation(final_plan)
    
    # Analyze field mapping
    analyze_field_mapping()
    
    print("\n🎯 SUMMARY:")
    print("1. Check if Planner Agent generates file operations")
    print("2. Verify field mapping between Planner output và Implementor input")
    print("3. Look for validation issues in debug_planner_output.json")
    print("4. If no file operations, check LLM prompt và codebase analysis")


if __name__ == "__main__":
    main()
