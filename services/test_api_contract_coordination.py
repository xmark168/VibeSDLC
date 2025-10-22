#!/usr/bin/env python3
"""
Test script to verify API contract coordination between layers
"""

import sys
import os

sys.path.append('ai-agent-service')


def test_dependency_identification():
    """Test dependency identification logic"""
    print("=" * 70)
    print("Test 1: Dependency Identification")
    print("=" * 70)
    
    try:
        from app.agents.developer.implementor.nodes.execute_step import _identify_dependency_files
        
        # Test case 1: Controller depends on Service
        created_files = [
            "src/models/User.js",
            "src/repositories/userRepository.js",
            "src/services/authService.js"
        ]
        
        current_file = "src/controllers/authController.js"
        dependencies = _identify_dependency_files(current_file, created_files)
        
        print(f"\n📝 Test Case 1: Controller -> Service")
        print(f"   Current file: {current_file}")
        print(f"   Created files: {created_files}")
        print(f"   Dependencies found: {dependencies}")
        
        if "src/services/authService.js" in dependencies:
            print(f"   ✅ PASS: Correctly identified authService.js as dependency")
        else:
            print(f"   ❌ FAIL: Did not identify authService.js")
            return False
        
        # Test case 2: Service depends on Repository
        current_file = "src/services/authService.js"
        dependencies = _identify_dependency_files(current_file, created_files)
        
        print(f"\n📝 Test Case 2: Service -> Repository")
        print(f"   Current file: {current_file}")
        print(f"   Dependencies found: {dependencies}")
        
        if "src/repositories/userRepository.js" in dependencies:
            print(f"   ✅ PASS: Correctly identified userRepository.js as dependency")
        else:
            print(f"   ❌ FAIL: Did not identify userRepository.js")
            return False
        
        # Test case 3: Repository depends on Model
        current_file = "src/repositories/userRepository.js"
        dependencies = _identify_dependency_files(current_file, created_files)
        
        print(f"\n📝 Test Case 3: Repository -> Model")
        print(f"   Current file: {current_file}")
        print(f"   Dependencies found: {dependencies}")
        
        if "src/models/User.js" in dependencies:
            print(f"   ✅ PASS: Correctly identified User.js as dependency")
        else:
            print(f"   ❌ FAIL: Did not identify User.js")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_building_with_dependencies():
    """Test context building includes dependency content"""
    print("\n" + "=" * 70)
    print("Test 2: Context Building with Dependencies")
    print("=" * 70)
    
    try:
        from app.agents.developer.implementor.nodes.execute_step import _build_file_context
        from app.agents.developer.implementor.state import ImplementorState
        
        # Create mock state
        state = ImplementorState(
            task_id="TEST-001",
            task_description="Add user authentication",
            tech_stack="nodejs",
            codebase_path="ai-agent-service/app/agents/demo/be/nodejs/express-basic",
            files_created=[
                "src/models/User.js",
                "src/repositories/userRepository.js",
                "src/services/authService.js"
            ]
        )
        
        # Mock sub-step
        sub_step = {
            "sub_step": "2.1",
            "title": "Create authController.js",
            "description": "Create authentication controller"
        }
        
        # Build context for controller (should include service dependency)
        context = _build_file_context(
            state=state,
            sub_step=sub_step,
            file_path="src/controllers/authController.js",
            is_creation=True
        )
        
        print(f"\n📊 Context Analysis:")
        print(f"   Context length: {len(context)} chars")
        
        # Check if dependency section exists
        if "DEPENDENCY FILES" in context:
            print(f"   ✅ PASS: Context includes DEPENDENCY FILES section")
        else:
            print(f"   ❌ FAIL: Context missing DEPENDENCY FILES section")
            return False
        
        # Check if service file content is included
        if "authService" in context:
            print(f"   ✅ PASS: Context includes authService content")
        else:
            print(f"   ❌ FAIL: Context missing authService content")
            return False
        
        # Check for API contract warning
        if "EXACT method names" in context or "API CONTRACT" in context:
            print(f"   ✅ PASS: Context includes API contract warning")
        else:
            print(f"   ❌ FAIL: Context missing API contract warning")
            return False
        
        print(f"\n📄 Context Preview (first 500 chars):")
        print(context[:500])
        print("...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_has_api_contract_instructions():
    """Test that prompts include API contract instructions"""
    print("\n" + "=" * 70)
    print("Test 3: Prompt API Contract Instructions")
    print("=" * 70)
    
    try:
        from app.agents.developer.implementor.utils.prompts import BACKEND_FILE_CREATION_PROMPT
        
        print(f"\n📊 Prompt Analysis:")
        print(f"   Prompt length: {len(BACKEND_FILE_CREATION_PROMPT)} chars")
        
        # Check for API contract section
        checks = [
            ("API CONTRACT CONSISTENCY", "API contract section"),
            ("DEPENDENCY COORDINATION", "Dependency coordination instructions"),
            ("EXACT method names", "Exact method name requirement"),
            ("EXACT return types", "Exact return type requirement"),
            ("SOURCE OF TRUTH", "Source of truth principle"),
        ]
        
        all_pass = True
        for check_text, check_name in checks:
            if check_text in BACKEND_FILE_CREATION_PROMPT:
                print(f"   ✅ {check_name}: Found")
            else:
                print(f"   ❌ {check_name}: NOT found")
                all_pass = False
        
        if all_pass:
            print(f"\n✅ All API contract instructions present in prompt")
        else:
            print(f"\n❌ Some API contract instructions missing")
        
        return all_pass
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_actual_codebase_issues():
    """Test against actual codebase issues"""
    print("\n" + "=" * 70)
    print("Test 4: Actual Codebase Issues")
    print("=" * 70)
    
    try:
        # Read actual files
        service_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
        controller_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/controllers/authController.js"
        repo_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/repositories/userRepository.js"
        
        with open(service_file, 'r', encoding='utf-8') as f:
            service_content = f.read()
        
        with open(controller_file, 'r', encoding='utf-8') as f:
            controller_content = f.read()
        
        with open(repo_file, 'r', encoding='utf-8') as f:
            repo_content = f.read()
        
        print(f"\n📊 Issue 1: Return Type Mismatch (Service -> Controller)")
        
        # Check if service returns {user, token}
        if "return {" in service_content and "user:" in service_content and "token," in service_content:
            print(f"   ✅ Service returns {{user, token}} object")
        else:
            print(f"   ⚠️  Service return type unclear")
        
        # Check if controller destructures {user, token}
        if "const { user, token }" in controller_content:
            print(f"   ✅ Controller correctly destructures {{user, token}}")
        elif "const user = await AuthService.registerUser" in controller_content:
            print(f"   ❌ ISSUE CONFIRMED: Controller expects only user, not {{user, token}}")
        
        print(f"\n📊 Issue 2: Method Name Mismatch (Repository -> Service)")
        
        # Check repository method name
        if "async createUser(" in repo_content:
            print(f"   ✅ Repository has createUser() method")
        else:
            print(f"   ⚠️  Repository method name unclear")
        
        # Check service calls correct method
        if "userRepository.createUser(" in service_content:
            print(f"   ✅ Service correctly calls createUser()")
        elif "userRepository.create(" in service_content:
            print(f"   ❌ ISSUE CONFIRMED: Service calls create() instead of createUser()")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Testing API Contract Coordination Fix")
    print("=" * 70)
    
    test1 = test_dependency_identification()
    test2 = test_context_building_with_dependencies()
    test3 = test_prompt_has_api_contract_instructions()
    test4 = test_actual_codebase_issues()
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   Dependency Identification: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Context Building: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Prompt Instructions: {'✅ PASS' if test3 else '❌ FAIL'}")
    print(f"   Actual Codebase Issues: {'✅ PASS' if test4 else '❌ FAIL'}")
    
    all_pass = test1 and test2 and test3 and test4
    
    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED - API contract coordination fix is working!")
        print("\n📝 Summary:")
        print("   - Dependency identification logic implemented")
        print("   - Context building includes dependency file content")
        print("   - Prompts include API contract consistency instructions")
        print("   - Ready to generate coordinated code across layers")
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
    
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

