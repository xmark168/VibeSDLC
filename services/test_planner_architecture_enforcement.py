#!/usr/bin/env python3
"""
Test script to verify Planner Agent architecture enforcement improvements
"""

import sys

sys.path.append("ai-agent-service")


def test_agents_md_optimization():
    """Test that AGENTS.md has been optimized"""
    print("=" * 70)
    print("Test 1: AGENTS.md Optimization")
    print("=" * 70)

    try:
        agents_md_path = (
            "ai-agent-service/app/agents/demo/be/nodejs/express-basic/AGENTS.md"
        )

        with open(agents_md_path, "r", encoding="utf-8") as f:
            content = f.read()

        line_count = len(content.splitlines())
        char_count = len(content)

        print("\n📊 AGENTS.md Statistics:")
        print(f"   Lines: {line_count}")
        print(f"   Characters: {char_count:,}")

        # Check if optimized (should be ~300 lines, not 1930)
        if line_count < 400:
            print(f"   ✅ PASS: File is optimized ({line_count} lines < 400)")
        else:
            print(f"   ❌ FAIL: File is still too long ({line_count} lines > 400)")
            return False

        # Check for critical sections
        critical_sections = [
            "CRITICAL IMPLEMENTATION RULES",
            "Layered Architecture",
            "Implementation Order",
            "Pattern #1: Model",
            "Pattern #2: Repository",
            "Pattern #3: Service",
            "Pattern #4: Controller",
            "Pattern #5: Routes",
        ]

        missing_sections = []
        for section in critical_sections:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            print("\n   ⚠️ Missing critical sections:")
            for section in missing_sections:
                print(f"      - {section}")
            return False
        else:
            print(f"\n   ✅ All {len(critical_sections)} critical sections present")

        # Check that redundant examples are removed
        redundant_markers = [
            "Step 1: Create Model",
            "Step 2: Create Repository",
            "Step 3: Create Service",
            "Step 4: Create Controller",
            "Step 5: Create Routes",
            "Step 6: Add Validation Schema",
            "Step 7: Register Routes",
            "Step 8: Create Tests",
        ]

        redundant_count = sum(1 for marker in redundant_markers if marker in content)

        if redundant_count > 0:
            print(
                f"\n   ⚠️ Warning: Found {redundant_count} redundant step-by-step examples"
            )
            print("      (These should be removed in optimized version)")
        else:
            print("\n   ✅ No redundant step-by-step examples found")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_planner_loads_full_agents_md():
    """Test that Planner Agent loads full AGENTS.md content"""
    print("\n" + "=" * 70)
    print("Test 2: Planner Agent Loads Full AGENTS.md")
    print("=" * 70)

    try:
        # Import directly from generate_plan module to avoid agent.py imports
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "generate_plan",
            "ai-agent-service/app/agents/developer/planner/nodes/generate_plan.py",
        )
        generate_plan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generate_plan)

        load_architecture_guidelines = generate_plan.load_architecture_guidelines
        _get_architecture_guidelines_text = (
            generate_plan._get_architecture_guidelines_text
        )

        # Load guidelines
        codebase_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        guidelines = load_architecture_guidelines(codebase_path)

        print("\n📊 Guidelines Loaded:")
        print(f"   Has AGENTS.md: {guidelines['has_agents_md']}")
        print(f"   Is Express Project: {guidelines['is_express_project']}")
        print(f"   Project Type: {guidelines['project_type']}")

        if not guidelines["has_agents_md"]:
            print("   ❌ FAIL: AGENTS.md not loaded")
            return False

        # Check that full content is loaded
        content = guidelines.get("architecture_content", "")
        content_length = len(content)

        print("\n📊 AGENTS.md Content:")
        print(f"   Length: {content_length:,} characters")

        if content_length < 1000:
            print("   ❌ FAIL: Content too short (not full AGENTS.md)")
            return False

        # Check for critical content
        critical_content = [
            "CRITICAL IMPLEMENTATION RULES",
            "Layered Architecture",
            "Model (Mongoose Schema)",
            "Repository (Data Access)",
            "Service (Business Logic)",
            "Controller (Request Handler)",
        ]

        missing_content = []
        for item in critical_content:
            if item not in content:
                missing_content.append(item)

        if missing_content:
            print("\n   ❌ FAIL: Missing critical content:")
            for item in missing_content:
                print(f"      - {item}")
            return False
        else:
            print(f"   ✅ All {len(critical_content)} critical content items present")

        # Test that _get_architecture_guidelines_text includes full content
        architecture_layers = {
            "has_models": True,
            "has_controllers": True,
            "has_routes": True,
            "has_services": False,
            "has_repositories": False,
        }

        guidelines_text = _get_architecture_guidelines_text(
            guidelines, architecture_layers
        )

        print("\n📊 Generated Guidelines Text:")
        print(f"   Length: {len(guidelines_text):,} characters")

        if "CRITICAL: FULL AGENTS.md ARCHITECTURE GUIDELINES" in guidelines_text:
            print("   ✅ Full AGENTS.md content is included in prompt")
        else:
            print("   ❌ FAIL: Full AGENTS.md content NOT included in prompt")
            return False

        if "MANDATORY REQUIREMENTS" in guidelines_text:
            print("   ✅ Mandatory requirements section present")
        else:
            print("   ❌ FAIL: Mandatory requirements section missing")
            return False

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_architecture_layer_detection():
    """Test that architecture layer detection works correctly"""
    print("\n" + "=" * 70)
    print("Test 3: Architecture Layer Detection")
    print("=" * 70)

    try:
        # Import directly from generate_plan module to avoid agent.py imports
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "generate_plan",
            "ai-agent-service/app/agents/developer/planner/nodes/generate_plan.py",
        )
        generate_plan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generate_plan)

        detect_express_architecture_layers = (
            generate_plan.detect_express_architecture_layers
        )

        codebase_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        layers = detect_express_architecture_layers(codebase_path)

        print("\n📊 Detected Layers:")
        for key, value in layers.items():
            if key.startswith("has_"):
                status = "✅" if value else "❌"
                print(f"   {status} {key}: {value}")

        # Expected layers (based on current codebase)
        expected = {
            "has_models": True,
            "has_controllers": True,
            "has_routes": True,
            "has_middleware": True,
        }

        # Missing layers (should be detected as missing)
        missing_expected = {
            "has_services": False,
            "has_repositories": False,
        }

        all_correct = True

        for key, expected_value in expected.items():
            if layers.get(key) != expected_value:
                print(
                    f"\n   ❌ FAIL: {key} should be {expected_value}, got {layers.get(key)}"
                )
                all_correct = False

        for key, expected_value in missing_expected.items():
            if layers.get(key) != expected_value:
                print(
                    f"\n   ⚠️ Warning: {key} should be {expected_value}, got {layers.get(key)}"
                )
                # Don't fail on this, just warn

        if all_correct:
            print("\n   ✅ All expected layers detected correctly")

        return all_correct

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Planner Agent Architecture Enforcement Improvements")
    print("=" * 70)

    test1 = test_agents_md_optimization()
    test2 = test_planner_loads_full_agents_md()
    test3 = test_architecture_layer_detection()

    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   AGENTS.md Optimization: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Planner Loads Full AGENTS.md: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Architecture Layer Detection: {'✅ PASS' if test3 else '❌ FAIL'}")

    all_pass = test1 and test2 and test3

    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED - Planner improvements are working!")
    else:
        print("❌ SOME TESTS FAILED - Review implementation")

    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
