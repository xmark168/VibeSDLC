#!/usr/bin/env python3
"""
Test script để verify prompt language fix
"""

import sys
import os

def test_prompt_content():
    """Test prompt content có explicit language requirements"""
    
    print("🧪 Testing Prompt Language Requirements")
    print("=" * 60)
    
    try:
        # Add to path
        sys.path.append("ai-agent-service/app")
        
        # Import prompts
        from agents.developer.implementor.utils.prompts import (
            BACKEND_FILE_CREATION_PROMPT,
            FRONTEND_FILE_CREATION_PROMPT,
            GENERIC_FILE_CREATION_PROMPT
        )
        
        print("✅ Successfully imported prompts")
        
        # Test BACKEND prompt
        print("\n📝 Testing BACKEND_FILE_CREATION_PROMPT:")
        
        # Check for language requirements
        backend_checks = [
            ("nodejs → JavaScript", 'tech_stack "nodejs": Generate JavaScript' in BACKEND_FILE_CREATION_PROMPT),
            ("fastapi → Python", 'tech_stack "fastapi": Generate Python' in BACKEND_FILE_CREATION_PROMPT),
            ("File extension matching", 'Match the file extension: .js = JavaScript' in BACKEND_FILE_CREATION_PROMPT),
            ("No language mixing", 'NEVER mix languages' in BACKEND_FILE_CREATION_PROMPT)
        ]
        
        for check_name, check_result in backend_checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
        
        # Test FRONTEND prompt
        print("\n📝 Testing FRONTEND_FILE_CREATION_PROMPT:")
        
        frontend_checks = [
            ("react-vite → JavaScript", 'tech_stack "react-vite": Generate JavaScript' in FRONTEND_FILE_CREATION_PROMPT),
            ("nextjs → JavaScript", 'tech_stack "nextjs": Generate JavaScript' in FRONTEND_FILE_CREATION_PROMPT),
            ("No Python for frontend", 'NEVER generate Python code for frontend' in FRONTEND_FILE_CREATION_PROMPT)
        ]
        
        for check_name, check_result in frontend_checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
        
        # Test GENERIC prompt
        print("\n📝 Testing GENERIC_FILE_CREATION_PROMPT:")
        
        generic_checks = [
            ("File extension matching", '.js files = JavaScript code ONLY' in GENERIC_FILE_CREATION_PROMPT),
            ("Python files", '.py files = Python code ONLY' in GENERIC_FILE_CREATION_PROMPT),
            ("No mixing warning", 'NEVER mix languages' in GENERIC_FILE_CREATION_PROMPT)
        ]
        
        for check_name, check_result in generic_checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
        
        # Count total checks
        all_checks = backend_checks + frontend_checks + generic_checks
        passed_checks = sum(1 for _, result in all_checks if result)
        total_checks = len(all_checks)
        
        print(f"\n📊 Overall: {passed_checks}/{total_checks} checks passed")
        
        return passed_checks == total_checks
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_prompt_formatting():
    """Test prompt formatting với tech stack"""
    
    print("\n🔧 Testing Prompt Formatting")
    print("=" * 60)
    
    try:
        from agents.developer.implementor.utils.prompts import BACKEND_FILE_CREATION_PROMPT
        
        # Test formatting với nodejs tech stack
        test_data = {
            "tech_stack": "nodejs",
            "implementation_plan": "Create validation utilities",
            "file_path": "src/utils/validation.js",
            "file_specs": "Email and password validation functions",
            "project_type": "existing_project"
        }
        
        formatted_prompt = BACKEND_FILE_CREATION_PROMPT.format(**test_data)
        
        print("✅ Prompt formatted successfully")
        
        # Check key elements in formatted prompt
        checks = [
            ("Tech stack mentioned", "nodejs" in formatted_prompt),
            ("File path mentioned", "validation.js" in formatted_prompt),
            ("Language requirements", "JavaScript/TypeScript code ONLY" in formatted_prompt),
            ("File extension rule", ".js = JavaScript" in formatted_prompt)
        ]
        
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
        
        # Show relevant excerpt
        print("\n📄 Language Requirements Section:")
        lines = formatted_prompt.split('\n')
        for i, line in enumerate(lines):
            if 'CRITICAL LANGUAGE REQUIREMENTS' in line:
                for j in range(i, min(i+8, len(lines))):
                    print(f"   {lines[j]}")
                break
        
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_validation_js_content():
    """Test validation.js content is now JavaScript"""
    
    print("\n🔍 Testing validation.js Content")
    print("=" * 60)
    
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/utils/validation.js"
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        print(f"✅ File found: {file_path}")
        print(f"📝 File size: {len(content)} characters")
        
        # Check for JavaScript patterns
        js_patterns = [
            ("Function declarations", "function " in content),
            ("Module exports", "module.exports" in content),
            ("JavaScript regex", "/^[a-zA-Z0-9" in content),
            ("JavaScript comments", "/**" in content),
            ("Const declarations", "const " in content)
        ]
        
        # Check for Python patterns (should be absent)
        python_patterns = [
            ("Python imports", "import re" not in content),
            ("Python functions", "def " not in content),
            ("Python regex", "r'^" not in content),
            ("Python returns", "return False," not in content)
        ]
        
        print("\n📊 JavaScript Patterns:")
        js_passed = 0
        for pattern_name, pattern_found in js_patterns:
            status = "✅" if pattern_found else "❌"
            print(f"   {status} {pattern_name}")
            if pattern_found:
                js_passed += 1
        
        print("\n📊 Python Patterns (should be absent):")
        py_passed = 0
        for pattern_name, pattern_absent in python_patterns:
            status = "✅" if pattern_absent else "❌"
            print(f"   {status} {pattern_name}")
            if pattern_absent:
                py_passed += 1
        
        total_js = len(js_patterns)
        total_py = len(python_patterns)
        
        print(f"\n📈 Results:")
        print(f"   JavaScript patterns: {js_passed}/{total_js}")
        print(f"   Python patterns absent: {py_passed}/{total_py}")
        
        return js_passed == total_js and py_passed == total_py
        
    else:
        print("❌ validation.js file not found")
        return False

def main():
    """Main test function"""
    
    print("🚀 Prompt Language Fix Verification")
    print("=" * 80)
    
    tests = [
        ("Prompt Content", test_prompt_content),
        ("Prompt Formatting", test_prompt_formatting),
        ("validation.js Content", test_validation_js_content)
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
    print("📊 FIX VERIFICATION SUMMARY")
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
        print("\n🎉 Language Fix Successfully Applied!")
        print("\n✅ Key Improvements:")
        print("   - Added explicit language requirements to all prompts")
        print("   - Specified tech stack → language mapping")
        print("   - Added file extension → language rules")
        print("   - Included 'NEVER mix languages' warnings")
        print("   - validation.js now contains proper JavaScript code")
        
        print("\n🚀 Developer Agent should now generate correct language code!")
        
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
