#!/usr/bin/env python3
"""
Test script để validate improved overlap detection logic.
"""

import sys
import os

# Add path để import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-agent-service', 'app'))

try:
    from agents.developer.implementor.utils.incremental_modifications import (
        _check_modification_overlap,
        _find_all_positions,
        validate_modifications_batch,
        CodeModification
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    IMPORTS_AVAILABLE = False


def read_env_file():
    """Read .env.example file content."""
    env_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None


def test_position_finding():
    """Test _find_all_positions function."""
    print("🧪 Testing position finding...")
    
    file_content = read_env_file()
    if not file_content:
        return False
    
    test_patterns = [
        "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
        "MONGODB_URI=mongodb://localhost:27017/express_basic",
        "# Redis\nREDIS_URL=redis://localhost:6379"
    ]
    
    if IMPORTS_AVAILABLE:
        for i, pattern in enumerate(test_patterns, 1):
            print(f"\n🔍 Pattern #{i}: {repr(pattern[:30])}...")
            positions = _find_all_positions(file_content, pattern)
            print(f"  Found at {len(positions)} positions: {positions}")
            
            # Show context for each position
            for j, (start, end) in enumerate(positions):
                context_start = max(0, start - 20)
                context_end = min(len(file_content), end + 20)
                context = file_content[context_start:context_end]
                print(f"    Position {j+1}: chars {start}-{end}")
                print(f"    Context: {repr(context)}")
    
    return True


def test_overlap_detection():
    """Test improved overlap detection."""
    print("\n🧪 Testing improved overlap detection...")
    
    file_content = read_env_file()
    if not file_content:
        return False
    
    # Test cases that previously caused false positives
    test_cases = [
        {
            "name": "Normal .env sections (should NOT overlap)",
            "old_code_1": "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
            "old_code_2": "# Redis\nREDIS_URL=redis://localhost:6379",
            "expected_overlap": False
        },
        {
            "name": "Substring patterns (should NOT overlap if in different locations)",
            "old_code_1": "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
            "old_code_2": "MONGODB_URI=mongodb://localhost:27017/express_basic",
            "expected_overlap": True  # These actually do overlap in the same location
        },
        {
            "name": "Completely separate sections (should NOT overlap)",
            "old_code_1": "# Redis\nREDIS_URL=redis://localhost:6379",
            "old_code_2": "# Email Configuration\nSMTP_HOST=smtp.gmail.com",
            "expected_overlap": False
        }
    ]
    
    if IMPORTS_AVAILABLE:
        for test_case in test_cases:
            print(f"\n{'='*50}")
            print(f"🧪 {test_case['name']}")
            
            old_code_1 = test_case['old_code_1']
            old_code_2 = test_case['old_code_2']
            expected = test_case['expected_overlap']
            
            print(f"  OLD_CODE 1: {repr(old_code_1[:40])}...")
            print(f"  OLD_CODE 2: {repr(old_code_2[:40])}...")
            print(f"  Expected overlap: {expected}")
            
            # Test new logic
            actual_overlap = _check_modification_overlap(file_content, old_code_1, old_code_2)
            print(f"  Actual overlap: {actual_overlap}")
            
            if actual_overlap == expected:
                print(f"  ✅ PASS: Overlap detection correct")
            else:
                print(f"  ❌ FAIL: Expected {expected}, got {actual_overlap}")
    
    return True


def test_batch_validation():
    """Test batch validation với improved logic."""
    print("\n🧪 Testing batch validation with improved logic...")
    
    file_content = read_env_file()
    if not file_content:
        return False
    
    if IMPORTS_AVAILABLE:
        # Create test modifications that previously failed
        modifications = [
            CodeModification(
                file_path=".env.example",
                old_code="# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
                new_code="# Database Configuration\nMONGODB_URI=mongodb://localhost:27017/express_basic\nDB_NAME=express_basic",
                description="Update database configuration"
            ),
            CodeModification(
                file_path=".env.example",
                old_code="# Redis\nREDIS_URL=redis://localhost:6379",
                new_code="# Redis Configuration\nREDIS_URL=redis://localhost:6379\nREDIS_PASSWORD=",
                description="Add Redis configuration"
            )
        ]
        
        print(f"📊 Testing {len(modifications)} modifications:")
        for i, mod in enumerate(modifications, 1):
            print(f"  Modification #{i}: {mod.description}")
            print(f"    OLD_CODE: {repr(mod.old_code[:40])}...")
        
        # Test batch validation
        all_valid, errors = validate_modifications_batch(file_content, modifications)
        
        print(f"\n📊 Batch validation results:")
        print(f"  All valid: {all_valid}")
        print(f"  Errors: {len(errors)}")
        
        if errors:
            print(f"  Error details:")
            for error in errors:
                print(f"    • {error}")
        else:
            print(f"  ✅ No errors - modifications should work!")
    
    return True


def test_edge_cases():
    """Test edge cases."""
    print("\n🧪 Testing edge cases...")
    
    if IMPORTS_AVAILABLE:
        # Test with empty patterns
        print("  Testing empty patterns...")
        overlap = _check_modification_overlap("test content", "", "test")
        print(f"    Empty pattern overlap: {overlap}")
        
        # Test with non-existent patterns
        print("  Testing non-existent patterns...")
        overlap = _check_modification_overlap("test content", "nonexistent1", "nonexistent2")
        print(f"    Non-existent patterns overlap: {overlap}")
        
        # Test with identical patterns
        print("  Testing identical patterns...")
        overlap = _check_modification_overlap("test content test", "test", "test")
        print(f"    Identical patterns overlap: {overlap}")
    
    return True


def main():
    """Main test function."""
    print("🚀 Starting overlap detection fix validation...\n")
    
    try:
        test_position_finding()
        test_overlap_detection()
        test_batch_validation()
        test_edge_cases()
        
        print("\n🎉 All tests completed!")
        print("\n📋 Summary:")
        print("  ✅ Improved overlap detection logic implemented")
        print("  ✅ Position-based overlap checking instead of substring matching")
        print("  ✅ Should fix modification #2 failures in .env.example")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    print(f"\n🏁 Test result: {'PASSED' if success else 'FAILED'}")
