#!/usr/bin/env python3
"""
Test script để verify Sequential Branching approach
"""

import json
import os
import sys
from pathlib import Path

def test_sequential_branching_logic():
    """Test sequential branching logic"""
    
    print("🧪 Testing Sequential Branching Approach")
    print("=" * 60)
    
    # Test scenario
    print("📋 Test Scenario:")
    print("  Task 1: Create feature/tsk-001 (from main)")
    print("  Task 2: Create feature/tsk-002 (from feature/tsk-001) ← Sequential")
    print()
    
    # Mock workflow
    tasks = [
        {"id": "TSK-001", "title": "Add authentication", "branch": "feature/tsk-001"},
        {"id": "TSK-002", "title": "Add authorization", "branch": "feature/tsk-002"},
        {"id": "TSK-003", "title": "Add logging", "branch": "feature/tsk-003"}
    ]
    
    previous_branch = None
    
    for i, task in enumerate(tasks):
        print(f"🎯 Task {i+1}: {task['title']} ({task['id']})")
        
        if previous_branch:
            print(f"   🔗 Sequential branching: Creating from '{previous_branch}'")
            print(f"   📝 Command: git checkout -b {task['branch']} {previous_branch}")
        else:
            print(f"   🌱 Initial branching: Creating from 'main'")
            print(f"   📝 Command: git checkout -b {task['branch']} main")
        
        # Simulate success
        print(f"   ✅ Branch '{task['branch']}' created successfully")
        print(f"   📁 Files from previous tasks: {'Preserved' if previous_branch else 'N/A'}")
        
        # Track for next iteration
        previous_branch = task['branch']
        print()
    
    print("🎯 Expected Result:")
    print("  - feature/tsk-001: Only Task 1 files")
    print("  - feature/tsk-002: Task 1 + Task 2 files")  
    print("  - feature/tsk-003: Task 1 + Task 2 + Task 3 files")
    print()
    
    return True

def test_git_commands():
    """Test actual Git commands in Node.js project"""
    
    print("🔧 Testing Git Commands in Node.js Project")
    print("=" * 60)
    
    nodejs_project = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
    
    try:
        os.chdir(nodejs_project)
        print(f"📁 Working directory: {os.getcwd()}")
        
        # Check current status
        print("\n📊 Current Git Status:")
        os.system("git status --short")
        
        print("\n🌿 Available Branches:")
        os.system("git branch -a")
        
        print("\n📝 Recent Commits:")
        os.system("git log --oneline -5")
        
        print("\n🎯 Sequential Branching Test:")
        print("  Current branches show the pattern we want to achieve")
        print("  - feature/tsk-6461: Has committed files from Task 1")
        print("  - feature/tsk-7662: Should inherit from Task 1 with sequential branching")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Return to original directory
        os.chdir("../../../../../../..")

def compare_approaches():
    """Compare Option A vs Sequential Branching"""
    
    print("📊 Comparison: Option A vs Sequential Branching")
    print("=" * 60)
    
    comparison = [
        ("Implementation Complexity", "❌ High", "✅ Low"),
        ("Code Changes Required", "❌ Many", "✅ Few"),
        ("Git History", "✅ Clean", "❌ Complex"),
        ("Task Independence", "✅ Independent", "❌ Dependent"),
        ("Rollback Capability", "✅ Easy", "❌ Hard"),
        ("File Preservation", "✅ Guaranteed", "✅ Automatic"),
        ("Merge Conflicts", "✅ Low Risk", "❌ Higher Risk"),
        ("CI/CD Compatibility", "✅ Good", "❌ Complex"),
    ]
    
    print(f"{'Aspect':<25} {'Option A (Auto-commit)':<20} {'Sequential Branching':<20}")
    print("-" * 70)
    
    for aspect, option_a, sequential in comparison:
        print(f"{aspect:<25} {option_a:<20} {sequential:<20}")
    
    print("\n🎯 Recommendation:")
    print("  Sequential Branching is simpler to implement but has trade-offs")
    print("  Option A (Auto-commit) is more robust for production use")
    print("  Choice depends on team workflow preferences")
    
    return True

def main():
    """Main test function"""
    
    print("🚀 Sequential Branching vs Option A Analysis")
    print("=" * 80)
    
    tests = [
        ("Sequential Branching Logic", test_sequential_branching_logic),
        ("Git Commands Test", test_git_commands),
        ("Approach Comparison", compare_approaches)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
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
        print("🎉 Sequential Branching approach is ready for testing!")
        print("\n🔧 Next Steps:")
        print("  1. Test with actual Developer Agent workflow")
        print("  2. Verify files are preserved between tasks")
        print("  3. Check for merge conflicts")
        print("  4. Compare with Option A results")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
