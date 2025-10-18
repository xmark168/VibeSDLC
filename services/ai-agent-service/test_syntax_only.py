#!/usr/bin/env python3
"""
Simple syntax test for Daytona integration files.
"""

import ast
import os


def test_file_syntax(file_path):
    """Test if a Python file has valid syntax."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        ast.parse(content)
        print(f"✅ {file_path}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"❌ {file_path}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {file_path}: Error - {e}")
        return False


def main():
    """Test syntax of all modified files."""
    print("🧪 Testing Syntax of Daytona Integration Files")
    print("=" * 60)

    files_to_test = [
        "app/agents/developer/planner/nodes/initialize_sandbox.py",
        "app/agents/developer/planner/state.py",
        "app/agents/developer/planner/agent.py",
        "app/agents/developer/planner/nodes/__init__.py",
        "app/agents/developer/planner/nodes/analyze_codebase.py",
    ]

    results = []
    for file_path in files_to_test:
        if os.path.exists(file_path):
            result = test_file_syntax(file_path)
            results.append((file_path, result))
        else:
            print(f"⚠️  {file_path}: File not found")
            results.append((file_path, False))

    print("\n" + "=" * 60)
    print("📊 SYNTAX TEST RESULTS")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for file_path, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {file_path}: {status}")

    print(f"\n🎯 Overall: {passed}/{total} files passed syntax check")

    if passed == total:
        print("🎉 All files have valid syntax!")
        return 0
    else:
        print("⚠️  Some files have syntax errors.")
        return 1


if __name__ == "__main__":
    exit(main())
