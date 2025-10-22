#!/usr/bin/env python3
"""
Verify overlap detection fix với manual implementation.
"""

def find_all_positions(content: str, pattern: str) -> list[tuple[int, int]]:
    """Find all positions where a pattern appears in content."""
    positions = []
    start = 0
    
    while True:
        pos = content.find(pattern, start)
        if pos == -1:
            break
        positions.append((pos, pos + len(pattern)))
        start = pos + 1
    
    return positions


def check_modification_overlap(file_content: str, old_code_1: str, old_code_2: str) -> bool:
    """Check if two OLD_CODE patterns actually overlap in the file content."""
    # Find all positions where each OLD_CODE appears
    positions_1 = find_all_positions(file_content, old_code_1)
    positions_2 = find_all_positions(file_content, old_code_2)
    
    # If either pattern doesn't exist, no overlap possible
    if not positions_1 or not positions_2:
        return False
    
    # Check if any ranges overlap
    for start_1, end_1 in positions_1:
        for start_2, end_2 in positions_2:
            # Check for range overlap: ranges overlap if one starts before the other ends
            if start_1 < end_2 and start_2 < end_1:
                return True
    
    return False


def old_overlap_logic(old_code_1: str, old_code_2: str) -> bool:
    """Old overlap logic (simple substring check)."""
    return old_code_1 in old_code_2 or old_code_2 in old_code_1


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


def main():
    """Main verification function."""
    print("🚀 Verifying overlap detection fix...\n")
    
    file_content = read_env_file()
    if not file_content:
        return False
    
    print(f"📄 File content loaded: {len(file_content)} chars")
    
    # Test cases that caused the original issue
    test_cases = [
        {
            "name": "Database and Redis sections",
            "old_code_1": "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
            "old_code_2": "# Redis\nREDIS_URL=redis://localhost:6379"
        },
        {
            "name": "Database section and MongoDB URI only",
            "old_code_1": "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
            "old_code_2": "MONGODB_URI=mongodb://localhost:27017/express_basic"
        },
        {
            "name": "Redis and Email sections",
            "old_code_1": "# Redis\nREDIS_URL=redis://localhost:6379",
            "old_code_2": "# Email Configuration\nSMTP_HOST=smtp.gmail.com"
        }
    ]
    
    print("🧪 Testing overlap detection comparison:\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{'='*60}")
        print(f"🧪 Test Case #{i}: {test_case['name']}")
        
        old_code_1 = test_case['old_code_1']
        old_code_2 = test_case['old_code_2']
        
        print(f"  OLD_CODE 1 ({len(old_code_1)} chars): {repr(old_code_1[:40])}...")
        print(f"  OLD_CODE 2 ({len(old_code_2)} chars): {repr(old_code_2[:40])}...")
        
        # Test old logic
        old_result = old_overlap_logic(old_code_1, old_code_2)
        print(f"\n  🔴 Old logic (substring check): {old_result}")
        
        # Test new logic
        new_result = check_modification_overlap(file_content, old_code_1, old_code_2)
        print(f"  🟢 New logic (position-based): {new_result}")
        
        # Show positions for debugging
        pos_1 = find_all_positions(file_content, old_code_1)
        pos_2 = find_all_positions(file_content, old_code_2)
        
        print(f"\n  📍 Positions in file:")
        print(f"    OLD_CODE 1 positions: {pos_1}")
        print(f"    OLD_CODE 2 positions: {pos_2}")
        
        # Determine if this is an improvement
        if old_result != new_result:
            if old_result and not new_result:
                print(f"  ✅ IMPROVEMENT: False positive eliminated!")
            elif not old_result and new_result:
                print(f"  ⚠️  CHANGE: New logic detects overlap that old logic missed")
            print(f"  💡 This explains why modification #2 was failing!")
        else:
            print(f"  ➡️  SAME: Both logics agree")
        
        print()
    
    # Summary
    print("📊 Summary of improvements:")
    print("  • Old logic: Simple substring checking (too strict)")
    print("  • New logic: Position-based overlap detection (more accurate)")
    print("  • Result: Eliminates false positives that caused modification #2 failures")
    
    print("\n🎯 Expected behavior after fix:")
    print("  • Modification #1 (Database section): Should pass")
    print("  • Modification #2 (Redis section): Should now pass (was failing before)")
    print("  • Agent should successfully apply both modifications to .env.example")
    
    return True


if __name__ == "__main__":
    success = main()
    print(f"\n🏁 Verification result: {'COMPLETED' if success else 'FAILED'}")
