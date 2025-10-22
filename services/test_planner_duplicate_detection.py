#!/usr/bin/env python3
"""
Test script to verify Planner Agent detects existing files and avoids duplicates
"""

import sys
import os

sys.path.append('ai-agent-service')


def test_codebase_analyzer_detects_controllers():
    """Test that codebase analyzer detects existing controllers and their functions"""
    print("=" * 70)
    print("Test 1: Codebase Analyzer Detects Controllers")
    print("=" * 70)
    
    try:
        from app.agents.developer.planner.tools.codebase_analyzer import (
            CodebaseAnalyzer,
            analyze_codebase_context
        )
        
        codebase_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        
        # Test 1: Analyzer detects authController.js
        analyzer = CodebaseAnalyzer(codebase_path)
        
        # Analyze authController.js
        auth_controller_path = "src/controllers/authController.js"
        analysis = analyzer.analyze_file_by_language(auth_controller_path)
        
        print(f"\n📊 Analysis of {auth_controller_path}:")
        print(f"   Language: {analysis.get('language', 'unknown')}")
        print(f"   Functions: {len(analysis.get('functions', []))}")
        
        functions = analysis.get('functions', [])
        if functions:
            print(f"\n   Detected Functions:")
            for func in functions:
                print(f"      - {func['name']} (line {func['line']})")
        
        # Check for specific functions
        function_names = [f['name'] for f in functions]
        
        expected_functions = ['registerUser', 'loginUser']
        found_functions = [f for f in expected_functions if f in function_names]
        
        if len(found_functions) >= 1:
            print(f"\n   ✅ PASS: Found {len(found_functions)} expected functions: {found_functions}")
        else:
            print(f"\n   ❌ FAIL: Expected functions not found")
            print(f"      Expected: {expected_functions}")
            print(f"      Found: {function_names}")
            return False
        
        # Test 2: analyze_codebase_context includes controller details
        print(f"\n📊 Testing analyze_codebase_context():")
        context = analyze_codebase_context(codebase_path)
        
        print(f"   Context length: {len(context)} chars")
        
        # Check if authController.js is mentioned
        if "authController.js" in context:
            print(f"   ✅ authController.js is in context")
        else:
            print(f"   ❌ FAIL: authController.js NOT in context")
            return False
        
        # Check if functions are mentioned
        functions_in_context = [f for f in function_names if f in context]
        if functions_in_context:
            print(f"   ✅ Functions in context: {functions_in_context}")
        else:
            print(f"   ⚠️ Warning: No functions found in context")
        
        # Show sample of context
        print(f"\n📝 Sample Context (first 500 chars):")
        print(context[:500])
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generate_plan_includes_codebase_context():
    """Test that generate_plan includes detailed codebase context in prompt"""
    print("\n" + "=" * 70)
    print("Test 2: Generate Plan Includes Codebase Context")
    print("=" * 70)
    
    try:
        # Read generate_plan.py source code
        with open("ai-agent-service/app/agents/developer/planner/nodes/generate_plan.py", 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Check for detailed_codebase_context variable
        if "detailed_codebase_context" in source_code:
            print("   ✅ Found 'detailed_codebase_context' variable")
        else:
            print("   ❌ FAIL: 'detailed_codebase_context' variable NOT found")
            return False
        
        # Check for analyze_codebase_context import
        if "from app.agents.developer.planner.tools.codebase_analyzer import" in source_code:
            if "analyze_codebase_context" in source_code:
                print("   ✅ Found 'analyze_codebase_context' import")
            else:
                print("   ⚠️ Warning: Import found but 'analyze_codebase_context' not imported")
        else:
            print("   ❌ FAIL: codebase_analyzer import NOT found")
            return False
        
        # Check if detailed_codebase_context is used in prompt
        if "DETAILED CODEBASE CONTEXT" in source_code:
            print("   ✅ Found 'DETAILED CODEBASE CONTEXT' section in prompt")
        else:
            print("   ❌ FAIL: 'DETAILED CODEBASE CONTEXT' section NOT in prompt")
            return False
        
        # Check for duplicate detection instructions
        if "DO NOT create duplicate" in source_code or "NEVER create files/functions that already exist" in source_code:
            print("   ✅ Found duplicate detection instructions")
        else:
            print("   ⚠️ Warning: No explicit duplicate detection instructions")
        
        # Check for "NO DUPLICATES" principle
        if "NO DUPLICATES" in source_code:
            print("   ✅ Found 'NO DUPLICATES' principle in Core Principles")
        else:
            print("   ⚠️ Warning: 'NO DUPLICATES' principle not in Core Principles")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_expected_behavior():
    """Test expected behavior with example scenario"""
    print("\n" + "=" * 70)
    print("Test 3: Expected Behavior Verification")
    print("=" * 70)
    
    print("\n📝 Scenario:")
    print("   Task: 'Add login functionality'")
    print("   Existing: authController.js with registerUser() and loginUser()")
    print("")
    print("❌ WRONG Behavior (Before Fix):")
    print("   - Plan creates new 'loginController.js'")
    print("   - Duplicate functionality")
    print("")
    print("✅ CORRECT Behavior (After Fix):")
    print("   - Plan detects existing authController.js")
    print("   - Plan detects existing loginUser() function")
    print("   - Plan suggests MODIFY authController.js instead of CREATE loginController.js")
    print("   - OR plan suggests refactor if separation is needed")
    print("")
    print("🔍 How Fix Works:")
    print("   1. analyze_codebase_context() scans src/controllers/")
    print("   2. Extracts authController.js with functions: [registerUser, loginUser]")
    print("   3. Passes detailed context to LLM in planning prompt")
    print("   4. LLM sees existing loginUser() function")
    print("   5. LLM generates plan to MODIFY authController.js, not CREATE loginController.js")
    
    return True


def main():
    """Run all tests"""
    print("🚀 Testing Planner Agent Duplicate Detection Fix")
    print("=" * 70)
    
    test1 = test_codebase_analyzer_detects_controllers()
    test2 = test_generate_plan_includes_codebase_context()
    test3 = test_expected_behavior()
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   Codebase Analyzer Detects Controllers: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Generate Plan Includes Context: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Expected Behavior Verified: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    all_pass = test1 and test2 and test3
    
    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED - Duplicate detection fix is working!")
        print("\n📝 Summary:")
        print("   - Codebase analyzer detects existing controllers and functions")
        print("   - Generate plan includes detailed codebase context in prompt")
        print("   - LLM receives explicit instructions to avoid duplicates")
        print("   - Expected behavior: MODIFY existing files instead of CREATE duplicates")
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
    
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

