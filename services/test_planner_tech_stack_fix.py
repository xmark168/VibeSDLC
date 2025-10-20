#!/usr/bin/env python3
"""
Test script để verify Planner tech stack fix
"""

import sys
import os

def test_planner_state_tech_stack():
    """Test PlannerState có tech_stack field"""
    
    print("🧪 Testing PlannerState tech_stack field")
    print("=" * 60)
    
    try:
        # Add to path
        sys.path.append("ai-agent-service/app")
        
        # Import PlannerState
        from agents.developer.planner.state import PlannerState
        
        print("✅ Successfully imported PlannerState")
        
        # Create instance
        state = PlannerState()
        
        # Check if tech_stack field exists
        if hasattr(state, 'tech_stack'):
            print("✅ tech_stack field exists")
            print(f"   Default value: '{state.tech_stack}'")
            
            # Test setting value
            state.tech_stack = "nodejs"
            print(f"   Set to 'nodejs': '{state.tech_stack}'")
            
            return True
        else:
            print("❌ tech_stack field missing")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_planner_initialize_detection():
    """Test Planner initialize có tech stack detection"""
    
    print("\n🧪 Testing Planner initialize tech stack detection")
    print("=" * 60)
    
    try:
        # Import initialize function
        from agents.developer.planner.nodes.initialize import detect_tech_stack
        
        print("✅ Successfully imported detect_tech_stack function")
        
        # Test with Node.js project path
        nodejs_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        
        if os.path.exists(nodejs_path):
            detected_stack = detect_tech_stack(nodejs_path)
            print(f"✅ Detected tech stack for Node.js project: '{detected_stack}'")
            
            if detected_stack == "nodejs":
                print("✅ Correct detection: nodejs")
                return True
            else:
                print(f"❌ Wrong detection: expected 'nodejs', got '{detected_stack}'")
                return False
        else:
            print(f"⚠️ Test path not found: {nodejs_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_prompt_tech_stack_requirements():
    """Test prompts có tech stack requirements"""
    
    print("\n🧪 Testing Planner prompts tech stack requirements")
    print("=" * 60)
    
    try:
        # Import prompts
        from app.templates.prompts.developer.planner import (
            CODEBASE_ANALYSIS_PROMPT,
            GENERATE_PLAN_PROMPT
        )
        
        print("✅ Successfully imported prompts")
        
        # Check CODEBASE_ANALYSIS_PROMPT
        codebase_checks = [
            ("File extension requirements", "ALWAYS match file extensions to the detected tech stack" in CODEBASE_ANALYSIS_PROMPT),
            ("Node.js requirements", "Node.js/Express projects: Use .js files" in CODEBASE_ANALYSIS_PROMPT),
            ("Python requirements", "Python/FastAPI projects: Use .py files" in CODEBASE_ANALYSIS_PROMPT),
            ("No mixing warning", "NEVER generate .py files for Node.js projects" in CODEBASE_ANALYSIS_PROMPT),
            ("Tech stack placeholder", "{tech_stack}" in CODEBASE_ANALYSIS_PROMPT)
        ]
        
        print("\n📝 CODEBASE_ANALYSIS_PROMPT checks:")
        codebase_passed = 0
        for check_name, check_result in codebase_checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if check_result:
                codebase_passed += 1
        
        # Check GENERATE_PLAN_PROMPT
        generate_checks = [
            ("File path requirements", "CRITICAL FILE PATH REQUIREMENTS" in GENERATE_PLAN_PROMPT),
            ("Node.js migration format", "Node.js: migrations/YYYYMMDD_description.js" in GENERATE_PLAN_PROMPT),
            ("Python migration format", "Python: alembic/versions/YYYYMMDD_description.py" in GENERATE_PLAN_PROMPT),
            ("No mixing warning", "NEVER generate .py files for Node.js projects" in GENERATE_PLAN_PROMPT)
        ]
        
        print("\n📝 GENERATE_PLAN_PROMPT checks:")
        generate_passed = 0
        for check_name, check_result in generate_checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if check_result:
                generate_passed += 1
        
        total_checks = len(codebase_checks) + len(generate_checks)
        total_passed = codebase_passed + generate_passed
        
        print(f"\n📊 Overall: {total_passed}/{total_checks} checks passed")
        
        return total_passed == total_checks
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_analyze_codebase_tech_stack_usage():
    """Test analyze_codebase node sử dụng tech_stack"""
    
    print("\n🧪 Testing analyze_codebase tech_stack usage")
    print("=" * 60)
    
    try:
        # Read analyze_codebase.py file
        analyze_file = "ai-agent-service/app/agents/developer/planner/nodes/analyze_codebase.py"
        
        if os.path.exists(analyze_file):
            with open(analyze_file, 'r') as f:
                content = f.read()
            
            print("✅ Successfully read analyze_codebase.py")
            
            # Check for tech_stack usage
            checks = [
                ("Tech stack in format", "tech_stack=state.tech_stack" in content),
                ("Tech stack fallback", 'state.tech_stack or "unknown"' in content)
            ]
            
            passed = 0
            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
                if check_result:
                    passed += 1
            
            return passed == len(checks)
        else:
            print(f"❌ File not found: {analyze_file}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 Planner Tech Stack Fix Verification")
    print("=" * 80)
    
    tests = [
        ("PlannerState tech_stack field", test_planner_state_tech_stack),
        ("Initialize tech stack detection", test_planner_initialize_detection),
        ("Prompt tech stack requirements", test_prompt_tech_stack_requirements),
        ("analyze_codebase tech_stack usage", test_analyze_codebase_tech_stack_usage)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 PLANNER FIX VERIFICATION SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Planner Tech Stack Fix Successfully Applied!")
        print("\n✅ Key Improvements:")
        print("   - Added tech_stack field to PlannerState")
        print("   - Added tech stack detection to Planner initialize")
        print("   - Enhanced prompts with explicit file extension requirements")
        print("   - Added tech stack context to codebase analysis")
        print("   - Added tech stack context to plan generation")
        
        print("\n🚀 Planner should now generate correct file extensions!")
        print("\n📋 Expected behavior:")
        print("   - Node.js projects → .js files and .js migrations")
        print("   - Python projects → .py files and .py migrations")
        print("   - No more .py files for Node.js projects")
        
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
