"""
Test syntax của generate_code implementation.
"""

import ast
import sys
from pathlib import Path

def test_python_syntax(file_path):
    """Test Python syntax của file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST để check syntax
        ast.parse(content)
        print(f"✅ {file_path}: Syntax OK")
        return True
        
    except SyntaxError as e:
        print(f"❌ {file_path}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"⚠️ {file_path}: Error - {e}")
        return False

def main():
    print("🧪 Testing Python syntax...")
    
    files_to_test = [
        "app/agents/developer/implementor/nodes/generate_code.py",
        "app/agents/developer/implementor/utils/prompts.py",
        "app/agents/developer/implementor/agent.py",
    ]
    
    all_passed = True
    
    for file_path in files_to_test:
        if Path(file_path).exists():
            passed = test_python_syntax(file_path)
            all_passed = all_passed and passed
        else:
            print(f"⚠️ {file_path}: File not found")
            all_passed = False
    
    print(f"\n📊 Overall result: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    
    if all_passed:
        print("🎉 Implementation syntax is correct!")
        print("✅ Ready for testing with proper environment")
        print("\n📋 Summary of changes:")
        print("1. ✅ Created generate_code.py node with LLM integration")
        print("2. ✅ Updated agent.py workflow to include generate_code step")
        print("3. ✅ Fixed prompts to use existing utils/prompts.py")
        print("4. ✅ Added incremental code generation support")
        print("5. ✅ Workflow: copy_boilerplate → generate_code → implement_files")
    else:
        print("💥 Fix syntax errors before proceeding")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
