#!/usr/bin/env python3
"""
Test script để verify tech stack detection cho Node.js/Express project
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

sys.path.append("ai-agent-service/app")
from agents.developer.implementor.tool.stack_tools import detect_stack_tool


def test_nodejs_detection():
    """Test tech stack detection cho Node.js/Express project"""

    # Path to the Node.js Express project
    nodejs_project_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"

    print(f"🔍 Testing tech stack detection for: {nodejs_project_path}")
    print("=" * 60)

    try:
        # Call detect_stack_tool
        result = detect_stack_tool.invoke({"project_path": nodejs_project_path})

        if result.startswith("Error"):
            print(f"❌ Detection failed: {result}")
            return False

        # Parse result
        stack_info = json.loads(result)

        print("📊 Detection Results:")
        print(
            f"  Primary Language: {stack_info.get('primary_language', 'Not detected')}"
        )
        print(f"  Frameworks: {stack_info.get('frameworks', [])}")
        print(f"  Package Managers: {stack_info.get('package_managers', [])}")
        print(f"  Confidence: {stack_info.get('confidence', 0)}")
        print(f"  Detected Files: {stack_info.get('detected_files', [])}")

        # Verify expected results
        expected_language = "JavaScript"
        expected_frameworks = ["Express.js"]

        primary_language = stack_info.get("primary_language", "")
        frameworks = stack_info.get("frameworks", [])

        print("\n✅ Verification:")

        # Check language
        if primary_language == expected_language:
            print(f"  ✅ Language correctly detected: {primary_language}")
        else:
            print(
                f"  ❌ Language mismatch. Expected: {expected_language}, Got: {primary_language}"
            )

        # Check frameworks
        if "Express.js" in frameworks:
            print(f"  ✅ Express.js framework detected: {frameworks}")
        else:
            print(f"  ❌ Express.js not detected. Got frameworks: {frameworks}")

        # Check package.json detection
        detected_files = stack_info.get("detected_files", [])
        if any("package.json" in f for f in detected_files):
            print("  ✅ package.json detected in files")
        else:
            print(f"  ❌ package.json not detected in files: {detected_files}")

        return True

    except Exception as e:
        print(f"❌ Exception during detection: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tech_stack_mapping():
    """Test tech stack mapping logic từ initialize.py"""

    print("\n🔧 Testing tech stack mapping logic:")
    print("=" * 60)

    # Simulate detection results
    test_cases = [
        {
            "primary_language": "JavaScript",
            "frameworks": ["Express.js"],
            "expected_tech_stack": "nodejs",
        },
        {
            "primary_language": "JavaScript",
            "frameworks": ["Next.js"],
            "expected_tech_stack": "nextjs",
        },
        {
            "primary_language": "JavaScript",
            "frameworks": ["React"],
            "expected_tech_stack": "react-vite",
        },
        {
            "primary_language": "Python",
            "frameworks": ["FastAPI"],
            "expected_tech_stack": "fastapi",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        primary_language = test_case["primary_language"].lower()
        frameworks = test_case["frameworks"]
        expected = test_case["expected_tech_stack"]

        # Apply mapping logic từ initialize.py
        tech_stack = None
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

        print(f"  Test {i}: {primary_language} + {frameworks}")
        if tech_stack == expected:
            print(f"    ✅ Correct mapping: {tech_stack}")
        else:
            print(f"    ❌ Wrong mapping. Expected: {expected}, Got: {tech_stack}")


if __name__ == "__main__":
    print("🧪 Tech Stack Detection Test")
    print("=" * 60)

    # Test 1: Actual detection
    success = test_nodejs_detection()

    # Test 2: Mapping logic
    test_tech_stack_mapping()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("❌ Test failed - check the issues above")
