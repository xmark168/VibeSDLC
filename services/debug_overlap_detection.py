#!/usr/bin/env python3
"""
Debug script để test overlap detection logic.
"""

def test_overlap_detection():
    """Test overlap detection logic."""
    print("🧪 Testing overlap detection logic...")
    
    # Sample OLD_CODE patterns từ .env modifications
    old_codes = [
        "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
        "# Redis\nREDIS_URL=redis://localhost:6379"
    ]
    
    print(f"📊 Testing {len(old_codes)} OLD_CODE patterns:")
    for i, code in enumerate(old_codes, 1):
        print(f"  OLD_CODE #{i} ({len(code)} chars): {repr(code)}")
    
    # Test overlap logic (from validate_modifications_batch)
    print(f"\n🔍 Testing overlap detection...")
    overlaps_found = []
    
    for i, old_code_1 in enumerate(old_codes):
        for j, old_code_2 in enumerate(old_codes[i + 1 :], i + 1):
            print(f"\n  Comparing OLD_CODE #{i+1} vs OLD_CODE #{j+1}:")
            print(f"    Code 1: {repr(old_code_1[:50])}...")
            print(f"    Code 2: {repr(old_code_2[:50])}...")
            
            # Test both directions
            code1_in_code2 = old_code_1 in old_code_2
            code2_in_code1 = old_code_2 in old_code_1
            
            print(f"    Code 1 in Code 2: {code1_in_code2}")
            print(f"    Code 2 in Code 1: {code2_in_code1}")
            
            if code1_in_code2 or code2_in_code1:
                overlap_msg = f"Modifications {i + 1} and {j + 1} overlap"
                overlaps_found.append(overlap_msg)
                print(f"    ❌ OVERLAP DETECTED: {overlap_msg}")
            else:
                print(f"    ✅ No overlap")
    
    print(f"\n📊 Overlap detection results:")
    print(f"  Total overlaps found: {len(overlaps_found)}")
    for overlap in overlaps_found:
        print(f"    • {overlap}")
    
    return len(overlaps_found) == 0


def test_with_problematic_patterns():
    """Test với patterns có thể gây overlap false positive."""
    print("\n🧪 Testing with potentially problematic patterns...")
    
    # Test cases có thể gây false positive
    test_cases = [
        {
            "name": "Normal .env sections",
            "old_codes": [
                "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
                "# Redis\nREDIS_URL=redis://localhost:6379"
            ]
        },
        {
            "name": "Overlapping content",
            "old_codes": [
                "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
                "MONGODB_URI=mongodb://localhost:27017/express_basic\n\n# Redis"
            ]
        },
        {
            "name": "Substring patterns",
            "old_codes": [
                "MONGODB_URI=mongodb://localhost:27017/express_basic",
                "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic"
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*50}")
        print(f"🧪 Test case: {test_case['name']}")
        
        old_codes = test_case['old_codes']
        print(f"📊 Testing {len(old_codes)} patterns:")
        
        for i, code in enumerate(old_codes, 1):
            print(f"  Pattern #{i}: {repr(code[:40])}...")
        
        # Apply overlap detection logic
        overlaps = []
        for i, old_code_1 in enumerate(old_codes):
            for j, old_code_2 in enumerate(old_codes[i + 1 :], i + 1):
                if old_code_1 in old_code_2 or old_code_2 in old_code_1:
                    overlaps.append(f"Patterns {i + 1} and {j + 1} overlap")
        
        print(f"📊 Results:")
        if overlaps:
            print(f"  ❌ {len(overlaps)} overlaps detected:")
            for overlap in overlaps:
                print(f"    • {overlap}")
        else:
            print(f"  ✅ No overlaps detected")


def test_real_env_modifications():
    """Test với real .env modification patterns."""
    print("\n🧪 Testing with real .env modification patterns...")
    
    # Patterns that might actually be used by implementor agent
    real_patterns = [
        # Pattern 1: Database section update
        "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
        
        # Pattern 2: Redis section update  
        "# Redis\nREDIS_URL=redis://localhost:6379",
        
        # Pattern 3: Potential overlapping pattern
        "MONGODB_URI=mongodb://localhost:27017/express_basic",
        
        # Pattern 4: Multi-line section
        "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic\n\n# Redis",
    ]
    
    print(f"📊 Testing {len(real_patterns)} real patterns:")
    for i, pattern in enumerate(real_patterns, 1):
        print(f"  Pattern #{i} ({len(pattern)} chars):")
        print(f"    {repr(pattern)}")
    
    # Test all combinations
    print(f"\n🔍 Testing all pattern combinations...")
    total_combinations = 0
    overlaps_found = 0
    
    for i, pattern1 in enumerate(real_patterns):
        for j, pattern2 in enumerate(real_patterns[i + 1:], i + 1):
            total_combinations += 1
            
            overlap = pattern1 in pattern2 or pattern2 in pattern1
            if overlap:
                overlaps_found += 1
                print(f"  ❌ Overlap #{overlaps_found}: Pattern {i+1} vs Pattern {j+1}")
                print(f"    Pattern {i+1}: {repr(pattern1[:30])}...")
                print(f"    Pattern {j+1}: {repr(pattern2[:30])}...")
                
                # Show which direction caused overlap
                if pattern1 in pattern2:
                    print(f"    → Pattern {i+1} is substring of Pattern {j+1}")
                if pattern2 in pattern1:
                    print(f"    → Pattern {j+1} is substring of Pattern {i+1}")
    
    print(f"\n📊 Final results:")
    print(f"  Total combinations tested: {total_combinations}")
    print(f"  Overlaps found: {overlaps_found}")
    print(f"  Success rate: {((total_combinations - overlaps_found) / total_combinations * 100):.1f}%")
    
    if overlaps_found > 0:
        print(f"\n💡 This explains why modification #2 might fail!")
        print(f"   The overlap detection is too strict and causes false positives.")


def main():
    """Main debug function."""
    print("🚀 Starting overlap detection debug...\n")
    
    try:
        test_overlap_detection()
        test_with_problematic_patterns()
        test_real_env_modifications()
        
        print("\n🎉 Overlap detection debug completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    print(f"\n🏁 Debug result: {'COMPLETED' if success else 'FAILED'}")
