#!/usr/bin/env python3
"""
Script to trigger the agent and capture debug output.
"""

import subprocess
import sys
import os


def run_simple_modification_test():
    """Run a simple modification test to trigger debug output"""
    print("🔍 Running Simple Modification Test")
    print("=" * 50)

    # Create a simple test script that uses the validation directly
    test_script = """
import sys
sys.path.append('ai-agent-service/app/agents/developer/implementor/utils')

try:
    from incremental_modifications import validate_modifications_batch, CodeModification
    
    # Read file
    with open('ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example', 'r') as f:
        file_content = f.read()
    
    # Create a simple modification that should work
    modifications = [
        CodeModification(
            file_path=".env.example",
            old_code="NODE_ENV=development",
            new_code="NODE_ENV=production",
            description="Change NODE_ENV"
        )
    ]
    
    print("DEBUG: Testing simple modification...")
    is_valid, errors = validate_modifications_batch(file_content, modifications)
    
    print(f"Result: {is_valid}")
    if errors:
        for error in errors:
            print(f"Error: {error}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
"""

    # Write and run the test script
    with open("simple_test.py", "w", encoding="utf-8") as f:
        f.write(test_script)

    try:
        result = subprocess.run(
            [sys.executable, "simple_test.py"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"Return code: {result.returncode}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists("simple_test.py"):
            os.remove("simple_test.py")


def check_file_consistency():
    """Check if the .env.example file is consistent"""
    print("\n🔍 Checking File Consistency")
    print("=" * 40)

    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"

    try:
        # Read file multiple times to check for consistency
        contents = []
        for i in range(3):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            contents.append(content)
            print(f"Read {i + 1}: {len(content)} chars, hash: {hash(content)}")

        # Check if all reads are identical
        if all(content == contents[0] for content in contents):
            print("✅ File content is consistent across reads")
            return True
        else:
            print("❌ File content is inconsistent!")
            for i, content in enumerate(contents):
                print(f"  Read {i + 1}: {len(content)} chars")
            return False

    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False


def check_working_directory():
    """Check current working directory and file paths"""
    print("\n🔍 Checking Working Directory and Paths")
    print("=" * 50)

    print(f"Current working directory: {os.getcwd()}")

    # Check if the file exists from current directory
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"

    if os.path.exists(file_path):
        print(f"✅ File exists: {file_path}")

        # Get absolute path
        abs_path = os.path.abspath(file_path)
        print(f"Absolute path: {abs_path}")

        # Check file stats
        stat = os.stat(file_path)
        print(f"File size: {stat.st_size} bytes")
        print(f"Last modified: {stat.st_mtime}")

        return True
    else:
        print(f"❌ File does not exist: {file_path}")

        # Try to find the file
        print("🔍 Searching for .env.example files...")
        for root, dirs, files in os.walk("."):
            for file in files:
                if file == ".env.example":
                    found_path = os.path.join(root, file)
                    print(f"  Found: {found_path}")

        return False


def main():
    """Run all checks"""
    print("🚀 Debugging Agent Environment")
    print("=" * 60)

    dir_ok = check_working_directory()
    file_ok = check_file_consistency()
    test_ok = run_simple_modification_test()

    print("\n" + "=" * 60)
    print("📊 Debug Results:")
    print(f"   Working directory: {'✅ OK' if dir_ok else '❌ ISSUE'}")
    print(f"   File consistency: {'✅ OK' if file_ok else '❌ ISSUE'}")
    print(f"   Simple test: {'✅ OK' if test_ok else '❌ ISSUE'}")

    if all([dir_ok, file_ok, test_ok]):
        print("✅ Environment looks good - issue might be in agent execution context")
    else:
        print("❌ Found environment issues that could explain the agent failures")


if __name__ == "__main__":
    main()
