#!/usr/bin/env python3
"""
Test với realistic patterns mà implementor agent có thể generate.
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
    positions_1 = find_all_positions(file_content, old_code_1)
    positions_2 = find_all_positions(file_content, old_code_2)
    
    if not positions_1 or not positions_2:
        return False
    
    for start_1, end_1 in positions_1:
        for start_2, end_2 in positions_2:
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
    """Test với realistic agent-generated patterns."""
    print("🚀 Testing realistic implementor agent patterns...\n")
    
    file_content = read_env_file()
    if not file_content:
        return False
    
    # Realistic patterns that agent might generate for .env modifications
    realistic_scenarios = [
        {
            "name": "Scenario 1: Separate sections (typical case)",
            "description": "Agent modifies database and redis sections separately",
            "patterns": [
                "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
                "# Redis\nREDIS_URL=redis://localhost:6379"
            ],
            "should_overlap": False,
            "explanation": "Different sections, no overlap expected"
        },
        {
            "name": "Scenario 2: Section header vs content",
            "description": "Agent modifies section header and then content within",
            "patterns": [
                "# Database",
                "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic"
            ],
            "should_overlap": True,
            "explanation": "Second pattern contains first, legitimate overlap"
        },
        {
            "name": "Scenario 3: Adjacent sections",
            "description": "Agent modifies end of one section and start of next",
            "patterns": [
                "MONGODB_URI=mongodb://localhost:27017/express_basic\n\n# Redis",
                "# Redis\nREDIS_URL=redis://localhost:6379"
            ],
            "should_overlap": True,
            "explanation": "Patterns share the '# Redis' line"
        },
        {
            "name": "Scenario 4: Non-overlapping single lines",
            "description": "Agent modifies individual config lines",
            "patterns": [
                "MONGODB_URI=mongodb://localhost:27017/express_basic",
                "REDIS_URL=redis://localhost:6379"
            ],
            "should_overlap": False,
            "explanation": "Different lines, no overlap"
        },
        {
            "name": "Scenario 5: Substring but different locations",
            "description": "One pattern is substring but appears elsewhere",
            "patterns": [
                "PORT=3000",
                "SMTP_PORT=587"
            ],
            "should_overlap": False,
            "explanation": "PORT appears in both but at different file locations"
        }
    ]
    
    print("🧪 Testing realistic modification scenarios:\n")
    
    false_positives_fixed = 0
    total_scenarios = len(realistic_scenarios)
    
    for i, scenario in enumerate(realistic_scenarios, 1):
        print(f"{'='*70}")
        print(f"🧪 {scenario['name']}")
        print(f"📝 {scenario['description']}")
        print(f"💡 Expected: {scenario['explanation']}")
        
        patterns = scenario['patterns']
        expected_overlap = scenario['should_overlap']
        
        print(f"\n📄 Patterns:")
        for j, pattern in enumerate(patterns, 1):
            print(f"  Pattern {j}: {repr(pattern)}")
        
        # Test both logics
        old_result = old_overlap_logic(patterns[0], patterns[1])
        new_result = check_modification_overlap(file_content, patterns[0], patterns[1])
        
        print(f"\n🔍 Results:")
        print(f"  Expected overlap: {expected_overlap}")
        print(f"  Old logic result: {old_result}")
        print(f"  New logic result: {new_result}")
        
        # Show positions for debugging
        pos_1 = find_all_positions(file_content, patterns[0])
        pos_2 = find_all_positions(file_content, patterns[1])
        print(f"  Positions: {pos_1} vs {pos_2}")
        
        # Evaluate results
        old_correct = old_result == expected_overlap
        new_correct = new_result == expected_overlap
        
        print(f"\n📊 Evaluation:")
        print(f"  Old logic correct: {old_correct}")
        print(f"  New logic correct: {new_correct}")
        
        if not old_correct and new_correct:
            false_positives_fixed += 1
            print(f"  ✅ IMPROVEMENT: New logic fixes false positive!")
        elif old_correct and not new_correct:
            print(f"  ❌ REGRESSION: New logic introduces error!")
        elif old_correct and new_correct:
            print(f"  ✅ MAINTAINED: Both logics correct")
        else:
            print(f"  ❌ BOTH WRONG: Neither logic correct")
        
        print()
    
    # Summary
    print("📊 FINAL SUMMARY:")
    print(f"  Total scenarios tested: {total_scenarios}")
    print(f"  False positives fixed: {false_positives_fixed}")
    print(f"  Improvement rate: {(false_positives_fixed / total_scenarios * 100):.1f}%")
    
    if false_positives_fixed > 0:
        print(f"\n🎉 SUCCESS: New logic eliminates {false_positives_fixed} false positive(s)!")
        print(f"💡 This should fix the modification #2 failures in .env.example")
    else:
        print(f"\n🤔 No false positives eliminated in these test cases.")
        print(f"💡 The issue might be in different patterns or edge cases.")
    
    print(f"\n🔧 Key improvement:")
    print(f"  • Old logic: Simple substring check (can cause false positives)")
    print(f"  • New logic: Position-based overlap detection (more accurate)")
    print(f"  • Result: Better handling of complex modification patterns")
    
    return True


if __name__ == "__main__":
    success = main()
    print(f"\n🏁 Test result: {'COMPLETED' if success else 'FAILED'}")
