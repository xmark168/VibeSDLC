#!/usr/bin/env python3
"""
Debug script to test the exact validation process that's failing.
"""


def simulate_exact_validation():
    """Simulate the exact validation process"""
    print("🔍 Simulating Exact Validation Process")
    print("=" * 60)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"✅ Read file: {len(file_content)} chars")
        
        # Simulate the two modifications that agent is trying to apply
        modifications = [
            {
                "id": 1,
                "description": "Add JWT_SECRET variable",
                "old_code": """# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRE=1h
JWT_REFRESH_EXPIRE=7d
BCRYPT_ROUNDS=12""",
                "new_code": """# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRE=1h
JWT_REFRESH_EXPIRE=7d
BCRYPT_ROUNDS=12"""
            },
            {
                "id": 2,
                "description": "Add additional JWT configuration",
                "old_code": """# Database
MONGODB_URI=mongodb://localhost:27017/express_basic

# Redis
REDIS_URL=redis://localhost:6379""",
                "new_code": """# Database
MONGODB_URI=mongodb://localhost:27017/express_basic

# Redis
REDIS_URL=redis://localhost:6379

# Additional JWT Configuration
JWT_ALGORITHM=HS256
JWT_ISSUER=express-basic-app"""
            }
        ]
        
        print(f"\n📋 Testing {len(modifications)} modifications:")
        
        # Test each modification individually
        for mod in modifications:
            print(f"\n🔍 Testing Modification #{mod['id']}: {mod['description']}")
            print("-" * 50)
            
            old_code = mod['old_code']
            print(f"OLD_CODE: {len(old_code)} chars")
            print(f"Raw: {repr(old_code)}")
            
            # Test 1: Substring match
            print(f"\n📋 Test 1: Substring match")
            old_code_stripped = old_code.strip()
            if old_code_stripped in file_content:
                print(f"✅ Substring match PASSED")
            else:
                print(f"❌ Substring match FAILED")
                continue
            
            # Test 2: Uniqueness
            print(f"\n📋 Test 2: Uniqueness check")
            count = file_content.count(old_code_stripped)
            print(f"OLD_CODE appears {count} times in file")
            if count == 1:
                print(f"✅ Uniqueness check PASSED")
            elif count == 0:
                print(f"❌ Uniqueness check FAILED - not found")
                continue
            else:
                print(f"❌ Uniqueness check FAILED - multiple matches")
                continue
            
            # Test 3: Line boundaries (if multi-line)
            print(f"\n📋 Test 3: Line boundaries check")
            if "\n" in old_code_stripped:
                file_lines = file_content.splitlines()
                old_lines = old_code_stripped.split("\n")
                
                print(f"File has {len(file_lines)} lines")
                print(f"OLD_CODE has {len(old_lines)} lines")
                
                # Find exact match
                found_start = -1
                for i in range(len(file_lines) - len(old_lines) + 1):
                    match = True
                    for j, old_line in enumerate(old_lines):
                        if i + j >= len(file_lines) or file_lines[i + j] != old_line:
                            match = False
                            break
                    if match:
                        found_start = i
                        break
                
                if found_start != -1:
                    print(f"✅ Line boundaries check PASSED (found at line {found_start + 1})")
                else:
                    print(f"❌ Line boundaries check FAILED")
                    
                    # Debug why it failed
                    print(f"🔍 Debugging line boundaries failure...")
                    for j, old_line in enumerate(old_lines):
                        print(f"  Expected line {j + 1}: {repr(old_line)}")
                        
                        # Find this line in file
                        found_at = []
                        for k, file_line in enumerate(file_lines):
                            if file_line == old_line:
                                found_at.append(k + 1)
                        
                        if found_at:
                            print(f"    Found at file lines: {found_at}")
                        else:
                            print(f"    NOT FOUND in file")
                            
                            # Check for similar lines
                            similar_at = []
                            for k, file_line in enumerate(file_lines):
                                if old_line.strip() == file_line.strip():
                                    similar_at.append(k + 1)
                            
                            if similar_at:
                                print(f"    Similar (content match) at lines: {similar_at}")
                    continue
            else:
                print(f"✅ Single line - no line boundaries check needed")
            
            print(f"✅ Modification #{mod['id']} validation PASSED")
        
        # Test 4: Overlap detection
        print(f"\n📋 Test 4: Overlap detection between modifications")
        print("-" * 50)
        
        old_codes = [mod['old_code'] for mod in modifications]
        
        for i, old_code_1 in enumerate(old_codes):
            for j, old_code_2 in enumerate(old_codes[i + 1:], i + 1):
                print(f"Checking overlap between modification {i + 1} and {j + 1}")
                
                # Simple substring check (old logic)
                if old_code_1 in old_code_2 or old_code_2 in old_code_1:
                    print(f"❌ Simple overlap detected")
                else:
                    print(f"✅ No simple overlap")
                
                # Position-based check (new logic)
                overlap_detected = check_modification_overlap(file_content, old_code_1, old_code_2)
                if overlap_detected:
                    print(f"❌ Position-based overlap detected")
                else:
                    print(f"✅ No position-based overlap")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_modification_overlap(file_content, old_code_1, old_code_2):
    """Check if two modifications overlap using position-based detection"""
    try:
        # Find positions of both OLD_CODEs in file
        positions_1 = find_all_positions(file_content, old_code_1.strip())
        positions_2 = find_all_positions(file_content, old_code_2.strip())
        
        if not positions_1 or not positions_2:
            return False  # One of them not found, no overlap
        
        # Check if any positions overlap
        for start_1, end_1 in positions_1:
            for start_2, end_2 in positions_2:
                # Check for overlap: ranges [start_1, end_1] and [start_2, end_2]
                if not (end_1 <= start_2 or end_2 <= start_1):
                    return True  # Overlap detected
        
        return False
        
    except Exception:
        return False


def find_all_positions(file_content, old_code):
    """Find all positions where old_code appears in file_content"""
    positions = []
    start = 0
    
    while True:
        pos = file_content.find(old_code, start)
        if pos == -1:
            break
        
        end_pos = pos + len(old_code)
        positions.append((pos, end_pos))
        start = pos + 1
    
    return positions


def main():
    """Run the exact validation simulation"""
    print("🚀 Debugging Exact Validation Process")
    print("=" * 70)
    
    success = simulate_exact_validation()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Validation simulation completed")
        print("💡 Check individual test results above to identify the failing step")
    else:
        print("❌ Validation simulation failed")


if __name__ == "__main__":
    main()
