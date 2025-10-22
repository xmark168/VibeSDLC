#!/usr/bin/env python3
"""
Direct test of codebase analyzer without importing planner agent
"""

import sys
import os
import importlib.util

def test_codebase_analyzer():
    """Test codebase analyzer directly"""
    print("=" * 70)
    print("Testing Codebase Analyzer - Direct Import")
    print("=" * 70)
    
    try:
        # Import codebase_analyzer module directly
        spec = importlib.util.spec_from_file_location(
            "codebase_analyzer",
            "ai-agent-service/app/agents/developer/planner/tools/codebase_analyzer.py"
        )
        codebase_analyzer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(codebase_analyzer)
        
        CodebaseAnalyzer = codebase_analyzer.CodebaseAnalyzer
        analyze_codebase_context = codebase_analyzer.analyze_codebase_context
        
        codebase_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        
        print(f"\n📊 Analyzing codebase at: {codebase_path}")
        
        # Test 1: Analyzer detects authController.js
        analyzer = CodebaseAnalyzer(codebase_path)
        
        # Analyze authController.js
        auth_controller_path = "src/controllers/authController.js"
        analysis = analyzer.analyze_file_by_language(auth_controller_path)
        
        print(f"\n📄 Analysis of {auth_controller_path}:")
        print(f"   Language: {analysis.get('language', 'unknown')}")
        print(f"   Lines: {analysis.get('lines', 0)}")
        print(f"   Functions: {len(analysis.get('functions', []))}")
        
        functions = analysis.get('functions', [])
        if functions:
            print(f"\n   Detected Functions:")
            for func in functions:
                print(f"      - {func['name']} (line {func['line']})")
        else:
            print(f"\n   ⚠️ No functions detected")
        
        # Check for specific functions
        function_names = [f['name'] for f in functions]
        
        expected_functions = ['registerUser', 'loginUser']
        found_functions = [f for f in expected_functions if f in function_names]
        
        if len(found_functions) >= 1:
            print(f"\n   ✅ PASS: Found {len(found_functions)} expected functions: {found_functions}")
            test1_pass = True
        else:
            print(f"\n   ❌ FAIL: Expected functions not found")
            print(f"      Expected: {expected_functions}")
            print(f"      Found: {function_names}")
            test1_pass = False
        
        # Test 2: analyze_codebase_context includes controller details
        print(f"\n📊 Testing analyze_codebase_context():")
        context = analyze_codebase_context(codebase_path)
        
        print(f"   Context length: {len(context)} chars")
        
        # Check if authController.js is mentioned
        if "authController.js" in context:
            print(f"   ✅ authController.js is in context")
            test2_pass = True
        else:
            print(f"   ❌ FAIL: authController.js NOT in context")
            test2_pass = False
        
        # Check if functions are mentioned
        functions_in_context = [f for f in function_names if f in context]
        if functions_in_context:
            print(f"   ✅ Functions in context: {functions_in_context}")
        else:
            print(f"   ⚠️ Warning: No functions found in context")
        
        # Show sample of context around authController
        if "authController.js" in context:
            idx = context.index("authController.js")
            sample_start = max(0, idx - 100)
            sample_end = min(len(context), idx + 400)
            print(f"\n📝 Context around authController.js:")
            print(context[sample_start:sample_end])
        
        return test1_pass and test2_pass
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run test"""
    print("🚀 Testing Codebase Analyzer (Direct Import)")
    print("=" * 70)
    
    success = test_codebase_analyzer()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ TEST PASSED - Codebase analyzer detects controllers and functions!")
    else:
        print("❌ TEST FAILED - Review implementation")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

