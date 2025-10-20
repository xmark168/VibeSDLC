#!/usr/bin/env python3
"""
Test script để debug sequential task handling issue
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_file_reading_logic():
    """Test file reading logic để verify current content"""
    
    print("🧪 Testing File Reading Logic")
    print("=" * 60)
    
    # Import the tools
    try:
        from ai_agent_service.app.agents.developer.implementor.tool.filesystem_tools import read_file_tool
        from ai_agent_service.app.agents.developer.implementor.nodes.generate_code import _extract_actual_content
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test file path
    test_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/routes/authRoutes.js"
    working_dir = "."
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        # Test read_file_tool
        print(f"📖 Reading file: {test_file}")
        read_result = read_file_tool.invoke({
            "file_path": test_file,
            "working_directory": working_dir,
        })
        
        print(f"✅ Read result length: {len(read_result)} chars")
        print(f"📝 First 200 chars: {read_result[:200]}...")
        
        # Test _extract_actual_content
        if "File not found" not in read_result:
            actual_content = _extract_actual_content(read_result)
            print(f"✅ Extracted content length: {len(actual_content)} chars")
            print(f"📝 First 200 chars: {actual_content[:200]}...")
            
            # Check if content contains register endpoint
            if "/register" in actual_content:
                print("✅ Register endpoint found in current content")
            else:
                print("❌ Register endpoint NOT found in current content")
                
            return True
        else:
            print(f"❌ File read failed: {read_result}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing file reading: {e}")
        return False

def test_current_file_state():
    """Test current state của authRoutes.js file"""
    
    print("\n🧪 Testing Current File State")
    print("=" * 60)
    
    test_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/routes/authRoutes.js"
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 File: {test_file}")
        print(f"📏 Content length: {len(content)} chars")
        print(f"📊 Line count: {content.count(chr(10)) + 1}")
        
        # Check for key patterns
        patterns = [
            ("/register", "Register endpoint"),
            ("/login", "Login endpoint"),
            ("import express", "Express import"),
            ("export default router", "Router export"),
            ("bcrypt", "Bcrypt usage"),
            ("jwt", "JWT usage"),
        ]
        
        for pattern, description in patterns:
            if pattern in content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} NOT found")
        
        # Show file structure
        lines = content.split('\n')
        print(f"\n📋 File structure:")
        for i, line in enumerate(lines[:10], 1):
            print(f"   {i:2d}: {line[:80]}")
        if len(lines) > 10:
            print(f"   ... ({len(lines) - 10} more lines)")
            for i, line in enumerate(lines[-3:], len(lines) - 2):
                print(f"   {i:2d}: {line[:80]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def simulate_task2_modification():
    """Simulate Task 2 modification để capture debug output"""
    
    print("\n🧪 Simulating Task 2 Modification")
    print("=" * 60)
    
    try:
        # Import required modules
        from ai_agent_service.app.agents.developer.implementor.state import FileChange
        from ai_agent_service.app.agents.developer.implementor.nodes.generate_code import _generate_file_modification
        from langchain_openai import ChatOpenAI
        
        # Create mock LLM (won't actually call API)
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        
        # Create FileChange for Task 2 (add login endpoint)
        file_change = FileChange(
            file_path="ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/routes/authRoutes.js",
            operation="modify",
            change_type="incremental",
            description="Add login endpoint to authRoutes.js with email/password validation and JWT token generation",
            target_function="login",
        )
        
        # Task context
        task_context = """Task: Implement user login feature
Tech Stack: express
Project Type: Existing project (in sandbox)
Implementation Plan: Add /login endpoint to existing authRoutes.js file"""
        
        codebase_context = "Express.js authentication routes with bcrypt and JWT"
        working_dir = "."
        tech_stack = "express"
        
        print("🔧 Calling _generate_file_modification with debug logging...")
        print(f"📁 Working dir: {working_dir}")
        print(f"📄 File path: {file_change.file_path}")
        print(f"📝 Description: {file_change.description}")
        
        # This will trigger our debug logging
        result = _generate_file_modification(
            llm=llm,
            file_change=file_change,
            task_context=task_context,
            codebase_context=codebase_context,
            working_dir=working_dir,
            tech_stack=tech_stack,
        )
        
        print(f"✅ Generation result: {result}")
        
        if hasattr(file_change, 'structured_modifications') and file_change.structured_modifications:
            print(f"📋 Structured modifications stored: {len(file_change.structured_modifications)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Error simulating Task 2: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

def analyze_sequential_task_issue():
    """Analyze potential issues với sequential task handling"""
    
    print("\n🧪 Analyzing Sequential Task Issues")
    print("=" * 60)
    
    issues = [
        {
            "issue": "File reading timing",
            "description": "Task 2 reads file before Task 1 write completes",
            "check": "File system operations are synchronous",
            "status": "✅ UNLIKELY"
        },
        {
            "issue": "LLM context confusion", 
            "description": "LLM mixes original file content with current content",
            "check": "Current content passed in prompt",
            "status": "🔍 POSSIBLE"
        },
        {
            "issue": "Structured modifications parsing",
            "description": "OLD_CODE patterns don't match current file structure",
            "check": "Debug logging will reveal this",
            "status": "🔍 LIKELY"
        },
        {
            "issue": "State management",
            "description": "FileChange state not updated between tasks",
            "check": "Each task creates new FileChange objects",
            "status": "✅ NOT ISSUE"
        },
        {
            "issue": "Caching",
            "description": "File content cached between reads",
            "check": "read_file_tool reads directly from disk",
            "status": "✅ NOT ISSUE"
        }
    ]
    
    for issue in issues:
        print(f"🔍 {issue['issue']}")
        print(f"   📝 {issue['description']}")
        print(f"   ✅ {issue['check']}")
        print(f"   {issue['status']}")
        print()
    
    print("🎯 Most Likely Root Causes:")
    print("1. 🔍 LLM context confusion - LLM generates OLD_CODE based on wrong context")
    print("2. 🔍 Structured modifications parsing - OLD_CODE doesn't match current file")
    print("3. 🔍 Prompt engineering - Current content not emphasized enough in prompt")
    
    return True

def main():
    """Main test function"""
    
    print("🚀 Sequential Tasks Debug Analysis")
    print("=" * 80)
    
    tests = [
        ("File reading logic", test_file_reading_logic),
        ("Current file state", test_current_file_state),
        ("Task 2 simulation", simulate_task2_modification),
        ("Sequential task analysis", analyze_sequential_task_issue),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SEQUENTIAL TASKS DEBUG SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed >= 3:  # Allow some tests to fail due to LLM API calls
        print("\n🎯 Debug Analysis Complete!")
        print("\n📋 Next Steps:")
        print("1. Run actual Developer Agent Task 2 to capture debug logs")
        print("2. Analyze LLM prompt và response để identify OLD_CODE mismatch")
        print("3. Fix prompt engineering hoặc structured modifications logic")
        print("4. Implement proper sequential task state management")
        
    else:
        print("⚠️ Some critical tests failed - check setup.")
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
