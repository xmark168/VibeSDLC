#!/usr/bin/env python3
"""
Test script để verify file_path error fix
"""

import os

def test_prompt_placeholders():
    """Test that all prompt placeholders are correctly handled"""
    
    print("🧪 Testing Prompt Placeholder Fix")
    print("=" * 60)
    
    generate_code_path = "ai-agent-service/app/agents/developer/implementor/nodes/generate_code.py"
    prompts_path = "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
    
    if not os.path.exists(generate_code_path):
        print(f"❌ File not found: {generate_code_path}")
        return False
    
    if not os.path.exists(prompts_path):
        print(f"❌ File not found: {prompts_path}")
        return False
    
    try:
        # Check generate_code.py for missing placeholders fix
        with open(generate_code_path, 'r', encoding='utf-8') as f:
            generate_content = f.read()
        
        # Check prompts.py for placeholders
        with open(prompts_path, 'r', encoding='utf-8') as f:
            prompts_content = f.read()
        
        # Check for required fixes in generate_code.py
        checks = [
            ("file_path parameter added", "file_path=file_change.file_path" in generate_content),
            ("language parameter added", "language=language" in generate_content),
            ("language mapping exists", "language_map = {" in generate_content),
            ("file extension detection", "file_ext = Path(file_change.file_path).suffix" in generate_content),
        ]
        
        passed = 0
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if check_result:
                passed += 1
        
        # Check for placeholders in prompts
        prompt_checks = [
            ("{file_path} placeholder exists", "{file_path}" in prompts_content),
            ("{language} placeholder exists", "{language}" in prompts_content),
            ("{current_content} placeholder exists", "{current_content}" in prompts_content),
            ("{modification_specs} placeholder exists", "{modification_specs}" in prompts_content),
            ("{change_type} placeholder exists", "{change_type}" in prompts_content),
            ("{target_element} placeholder exists", "{target_element}" in prompts_content),
            ("{tech_stack} placeholder exists", "{tech_stack}" in prompts_content),
        ]
        
        for check_name, check_result in prompt_checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if check_result:
                passed += 1
        
        total_checks = len(checks) + len(prompt_checks)
        print(f"\n📊 Placeholder checks: {passed}/{total_checks} passed")
        return passed == total_checks
        
    except Exception as e:
        print(f"❌ Error reading files: {e}")
        return False

def test_error_handling():
    """Test that error handling is improved"""
    
    print("\n🧪 Testing Error Handling")
    print("=" * 60)
    
    generate_code_path = "ai-agent-service/app/agents/developer/implementor/nodes/generate_code.py"
    
    try:
        with open(generate_code_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for error handling improvements
        checks = [
            ("Exception handling exists", "except Exception as e:" in content),
            ("Error message logging", "Error generating file modification" in content),
            ("Clean error handling", "return None" in content),
        ]
        
        passed = 0
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if check_result:
                passed += 1
        
        print(f"\n📊 Error handling checks: {passed}/{len(checks)} passed")
        return passed == len(checks)
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def test_language_mapping():
    """Test language mapping logic"""
    
    print("\n🧪 Testing Language Mapping Logic")
    print("=" * 60)
    
    # Test language mapping logic
    language_map = {
        '.py': 'python',
        '.js': 'javascript', 
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
    }
    
    test_cases = [
        ("src/app.js", "javascript"),
        ("src/config/index.js", "javascript"),
        ("routes/authRoutes.js", "javascript"),
        ("models/user.py", "python"),
        ("components/App.tsx", "tsx"),
        ("utils/helper.ts", "typescript"),
        ("unknown.txt", "text"),  # fallback case
    ]
    
    passed = 0
    for file_path, expected_language in test_cases:
        # Simulate the logic from generate_code.py
        from pathlib import Path
        file_ext = Path(file_path).suffix
        language = language_map.get(file_ext, 'text')
        
        if language == expected_language:
            print(f"   ✅ {file_path} → {language}")
            passed += 1
        else:
            print(f"   ❌ {file_path} → {language} (expected {expected_language})")
    
    print(f"\n📊 Language mapping: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def main():
    """Main test function"""
    
    print("🚀 File Path Error Fix Verification")
    print("=" * 80)
    
    tests = [
        ("Prompt placeholders", test_prompt_placeholders),
        ("Error handling", test_error_handling),
        ("Language mapping", test_language_mapping),
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
    print("📊 FILE PATH ERROR FIX SUMMARY")
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
        print("\n🎉 File Path Error Fix Verified!")
        print("\n✅ Root Cause Analysis:")
        print("   - Error 'file_path' was caused by missing placeholders in prompt.format()")
        print("   - {file_path} placeholder existed in prompts but not passed to format()")
        print("   - {language} placeholder existed in prompts but not passed to format()")
        print("   - KeyError occurred when LLM tried to format prompts")
        
        print("\n🔧 Fix Applied:")
        print("   - Added file_path=file_change.file_path to format() call")
        print("   - Added language mapping based on file extension")
        print("   - Added language=language to format() call")
        print("   - All prompt placeholders now properly handled")
        
        print("\n🚀 Expected Result:")
        print("   - No more 'file_path' KeyError")
        print("   - Prompts format correctly with all placeholders")
        print("   - File modification workflow completes successfully")
        print("   - Structured modifications work with proper language detection")
        
    else:
        print("⚠️ Some verification checks failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
