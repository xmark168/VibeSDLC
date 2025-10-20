#!/usr/bin/env python3
"""
Simple test để check tech stack detection logic
"""

import json
import os
from pathlib import Path

def test_package_json_detection():
    """Test detection logic cho package.json"""
    
    print("🧪 Testing package.json detection logic")
    print("=" * 50)
    
    # Path to Node.js project
    project_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
    package_json_path = os.path.join(project_path, "package.json")
    
    print(f"📁 Project path: {project_path}")
    print(f"📄 package.json path: {package_json_path}")
    
    # Check if package.json exists
    if os.path.exists(package_json_path):
        print("✅ package.json found")
        
        # Read and parse package.json
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            print("✅ package.json parsed successfully")
            
            # Check dependencies for Express
            dependencies = package_data.get('dependencies', {})
            dev_dependencies = package_data.get('devDependencies', {})
            all_deps = {**dependencies, **dev_dependencies}
            
            print(f"📦 Dependencies found: {len(all_deps)}")
            
            # Check for Express
            if 'express' in all_deps:
                print(f"✅ Express.js detected: {all_deps['express']}")
                return "nodejs"
            else:
                print("❌ Express.js not found in dependencies")
                return "javascript"
                
        except Exception as e:
            print(f"❌ Error parsing package.json: {e}")
            return None
    else:
        print("❌ package.json not found")
        return None

def test_tech_stack_mapping():
    """Test tech stack mapping logic"""
    
    print("\n🔧 Testing tech stack mapping")
    print("=" * 50)
    
    # Simulate detection results
    primary_language = "javascript"  # lowercase như trong code
    frameworks = ["Express.js"]
    
    print(f"📝 Input: language='{primary_language}', frameworks={frameworks}")
    
    # Apply mapping logic từ initialize.py
    tech_stack = ""
    
    if primary_language == "javascript":
        if "Express.js" in frameworks:
            tech_stack = "nodejs"
        elif "Next.js" in frameworks:
            tech_stack = "nextjs"
        elif "React" in frameworks:
            tech_stack = "react-vite"
        else:
            tech_stack = "nodejs"  # Default for JavaScript
    elif primary_language == "python":
        if "FastAPI" in frameworks:
            tech_stack = "fastapi"
        elif "Django" in frameworks:
            tech_stack = "django"
        elif "Flask" in frameworks:
            tech_stack = "flask"
        else:
            tech_stack = "python"
    else:
        tech_stack = primary_language or "unknown"
    
    print(f"✅ Mapped tech stack: '{tech_stack}'")
    
    # Verify expected result
    expected = "nodejs"
    if tech_stack == expected:
        print(f"✅ Correct mapping! Expected: {expected}, Got: {tech_stack}")
        return True
    else:
        print(f"❌ Wrong mapping! Expected: {expected}, Got: {tech_stack}")
        return False

def test_prompt_selection():
    """Test prompt selection logic"""
    
    print("\n🎯 Testing prompt selection")
    print("=" * 50)
    
    tech_stack = "nodejs"
    
    # Simulate prompt selection logic từ generate_code.py
    tech_stack_lower = tech_stack.lower()
    
    backend_stacks = [
        "fastapi", "django", "flask", "nodejs", "express", 
        "spring", "dotnet", "rails", "laravel", "go"
    ]
    
    frontend_stacks = [
        "react", "vue", "angular", "nextjs", "nuxtjs",
        "svelte", "gatsby", "vite"
    ]
    
    is_backend = any(stack in tech_stack_lower for stack in backend_stacks)
    is_frontend = any(stack in tech_stack_lower for stack in frontend_stacks)
    
    print(f"📝 Tech stack: {tech_stack}")
    print(f"📝 Is backend: {is_backend}")
    print(f"📝 Is frontend: {is_frontend}")
    
    if is_backend:
        prompt_type = "BACKEND_FILE_CREATION_PROMPT"
        print(f"✅ Selected prompt: {prompt_type}")
        return True
    elif is_frontend:
        prompt_type = "FRONTEND_FILE_CREATION_PROMPT"
        print(f"✅ Selected prompt: {prompt_type}")
        return True
    else:
        prompt_type = "GENERIC_FILE_CREATION_PROMPT"
        print(f"⚠️ Fallback prompt: {prompt_type}")
        return False

def analyze_validation_js():
    """Analyze the problematic validation.js file"""
    
    print("\n🔍 Analyzing validation.js file")
    print("=" * 50)
    
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/utils/validation.js"
    
    if os.path.exists(file_path):
        print(f"📄 File found: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        print(f"📝 File size: {len(content)} characters")
        print(f"📝 First few lines:")
        
        lines = content.split('\n')[:5]
        for i, line in enumerate(lines, 1):
            print(f"   {i}: {line}")
        
        # Check for Python syntax
        python_indicators = ['import re', 'def ', 'if not ', 'return False,']
        js_indicators = ['const ', 'function ', 'export ', 'module.exports']
        
        python_count = sum(1 for indicator in python_indicators if indicator in content)
        js_count = sum(1 for indicator in js_indicators if indicator in content)
        
        print(f"\n📊 Language indicators:")
        print(f"   Python indicators: {python_count}")
        print(f"   JavaScript indicators: {js_count}")
        
        if python_count > js_count:
            print("❌ File contains Python code (should be JavaScript)")
            return False
        else:
            print("✅ File contains JavaScript code")
            return True
    else:
        print("❌ validation.js file not found")
        return False

def main():
    """Main test function"""
    
    print("🚀 Tech Stack Detection Debug")
    print("=" * 60)
    
    tests = [
        ("package.json Detection", test_package_json_detection),
        ("Tech Stack Mapping", test_tech_stack_mapping),
        ("Prompt Selection", test_prompt_selection),
        ("validation.js Analysis", analyze_validation_js)
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
    print("\n" + "=" * 60)
    print("📊 DEBUG SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        if result == "nodejs":
            status = "✅ DETECTED nodejs"
        elif result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = f"ℹ️ RESULT: {result}"
        
        print(f"   {status} - {test_name}")
    
    print("\n🎯 Root Cause Analysis:")
    print("   1. Tech stack detection logic appears correct")
    print("   2. Mapping from JavaScript + Express.js → nodejs works")
    print("   3. Prompt selection should use BACKEND_FILE_CREATION_PROMPT")
    print("   4. validation.js contains Python code (PROBLEM!)")
    
    print("\n🔧 Likely Issues:")
    print("   - LLM is not following tech stack instructions in prompt")
    print("   - Prompt may not be explicit enough about language")
    print("   - Need to check actual prompt content sent to LLM")

if __name__ == "__main__":
    main()
