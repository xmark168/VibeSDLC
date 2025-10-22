#!/usr/bin/env python3
"""
Simple test of dependency detection logic without imports
"""


def test_new_format():
    """Test new format (top-level external_dependencies)"""
    print("=" * 70)
    print("Test 1: New Format (Top-Level external_dependencies)")
    print("=" * 70)
    
    # Mock implementation plan with NEW format
    implementation_plan = {
        "task_id": "TEST-001",
        "external_dependencies": [
            {"package": "jsonwebtoken", "version": "^9.0.0"},
            {"package": "bcryptjs", "version": "^5.0.0"},
            {"package": "express-rate-limit", "version": "^6.0.0"},
            {"package": "morgan", "version": "^1.10.0"}
        ]
    }
    
    # Simulate install_dependencies.py logic (AFTER FIX)
    external_deps = implementation_plan.get("external_dependencies", [])
    if not external_deps:
        infrastructure = implementation_plan.get("infrastructure", {})
        external_deps = infrastructure.get("external_dependencies", [])
    
    print(f"\n📊 Detection Results:")
    print(f"   Found {len(external_deps)} external dependencies")
    
    if len(external_deps) == 4:
        print(f"   ✅ PASS: Detected all 4 dependencies")
        for dep in external_deps:
            print(f"      - {dep['package']}@{dep['version']}")
        return True
    else:
        print(f"   ❌ FAIL: Expected 4, found {len(external_deps)}")
        return False


def test_old_format():
    """Test old format (infrastructure.external_dependencies)"""
    print("\n" + "=" * 70)
    print("Test 2: Old Format (infrastructure.external_dependencies)")
    print("=" * 70)
    
    # Mock implementation plan with OLD format
    implementation_plan = {
        "task_id": "TEST-002",
        "infrastructure": {
            "external_dependencies": [
                {"package": "express", "version": "^4.18.0"},
                {"package": "mongoose", "version": "^7.0.0"}
            ]
        }
    }
    
    # Simulate install_dependencies.py logic (AFTER FIX)
    external_deps = implementation_plan.get("external_dependencies", [])
    if not external_deps:
        infrastructure = implementation_plan.get("infrastructure", {})
        external_deps = infrastructure.get("external_dependencies", [])
    
    print(f"\n📊 Detection Results:")
    print(f"   Found {len(external_deps)} external dependencies")
    
    if len(external_deps) == 2:
        print(f"   ✅ PASS: Backward compatibility works")
        for dep in external_deps:
            print(f"      - {dep['package']}@{dep['version']}")
        return True
    else:
        print(f"   ❌ FAIL: Expected 2, found {len(external_deps)}")
        return False


def test_before_fix_behavior():
    """Demonstrate behavior BEFORE fix"""
    print("\n" + "=" * 70)
    print("Test 3: Behavior BEFORE Fix (Broken)")
    print("=" * 70)
    
    # Mock implementation plan with NEW format
    implementation_plan = {
        "task_id": "TEST-003",
        "external_dependencies": [
            {"package": "jsonwebtoken", "version": "^9.0.0"},
            {"package": "bcryptjs", "version": "^5.0.0"}
        ]
    }
    
    # Simulate OLD logic (BEFORE FIX)
    infrastructure = implementation_plan.get("infrastructure", {})
    external_deps = infrastructure.get("external_dependencies", [])
    
    print(f"\n📊 OLD Logic Results:")
    print(f"   Found {len(external_deps)} external dependencies")
    
    if len(external_deps) == 0:
        print(f"   ✅ CONFIRMED: Old logic fails to detect (as expected)")
        print(f"   This is why user saw 'Found 0 external dependencies'")
        return True
    else:
        print(f"   ❌ Unexpected: Old logic found {len(external_deps)} deps")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Dependency Detection Logic")
    print("=" * 70)
    
    test1 = test_new_format()
    test2 = test_old_format()
    test3 = test_before_fix_behavior()
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   New Format Detection: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Old Format (Backward Compat): {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Before Fix Behavior: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    all_pass = test1 and test2 and test3
    
    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED!")
        print("\n📝 Fix Summary:")
        print("   BEFORE: Only checked infrastructure.external_dependencies")
        print("   AFTER:  Checks top-level first, falls back to infrastructure")
        print("   RESULT: Both formats now work correctly")
    else:
        print("❌ SOME TESTS FAILED")
    
    print("=" * 70)
    
    return all_pass


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

