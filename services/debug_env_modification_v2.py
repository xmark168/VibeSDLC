#!/usr/bin/env python3
"""
Debug script to analyze the .env.example modification issue.
"""


def debug_env_modification():
    """Debug the .env.example modification issue"""
    print("🔍 Debugging .env.example Modification Issue")
    print("=" * 60)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"✅ Read file: {len(file_content)} chars")
        print(f"📄 File content preview:")
        lines = file_content.splitlines()
        for i, line in enumerate(lines[:10], 1):
            print(f"  {i:2d}: {line}")
        print(f"  ... (total {len(lines)} lines)")
        
        # From the error log, agent generated this modification
        sample_llm_output = """MODIFICATION #1:
FILE: `.env.example`
DESCRIPTION: Add a new variable `JWT_SECRET` to the `.env.example` file for environment configuration.

OLD_CODE:
```text
# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRE=1h
JWT_REFRESH_EXPIRE=7d
BCRYPT_ROUNDS=12
```

NEW_CODE:
```text
# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRE=1h
JWT_REFRESH_EXPIRE=7d
BCRYPT_ROUNDS=12
```

MODIFICATION #2:
FILE: `.env.example`
DESCRIPTION: Add additional environment variables for JWT configuration.

OLD_CODE:
```text
# Database
MONGODB_URI=mongodb://localhost:27017/express_basic

# Redis
REDIS_URL=redis://localhost:6379
```

NEW_CODE:
```text
# Database
MONGODB_URI=mongodb://localhost:27017/express_basic

# Redis
REDIS_URL=redis://localhost:6379

# Additional JWT Configuration
JWT_ALGORITHM=HS256
JWT_ISSUER=express-basic-app
```"""
        
        print(f"\n📋 Sample LLM output (simulated):")
        print(sample_llm_output[:300] + "...")
        
        # Test parsing
        import re
        
        print(f"\n🔍 Testing modification parsing...")
        
        # Split by MODIFICATION markers
        modification_blocks = re.split(r"MODIFICATION #\d+:", sample_llm_output)
        print(f"Found {len(modification_blocks)} blocks (including empty first)")
        
        modifications = []
        
        for i, block in enumerate(modification_blocks[1:], 1):  # Skip first empty block
            print(f"\n📋 Processing block {i}:")
            print(f"Block content: {block[:200]}...")
            
            try:
                # Extract file path
                file_match = re.search(r"FILE:\s*(.+)", block)
                if file_match:
                    file_path_extracted = file_match.group(1).strip()
                    print(f"  File: {file_path_extracted}")
                
                # Extract description
                desc_match = re.search(r"DESCRIPTION:\s*(.+)", block)
                if desc_match:
                    description = desc_match.group(1).strip()
                    print(f"  Description: {description[:50]}...")
                
                # Extract OLD_CODE
                old_code_match = re.search(
                    r"OLD_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
                )
                if old_code_match:
                    old_code = old_code_match.group(1)
                    print(f"  OLD_CODE: {len(old_code)} chars")
                    print(f"    Raw: {repr(old_code[:100])}...")
                    
                    # Test if OLD_CODE exists in file
                    if old_code.strip() in file_content:
                        print(f"    ✅ Found in file")
                    else:
                        print(f"    ❌ NOT found in file")
                        
                        # Check line by line
                        old_lines = old_code.split('\n')
                        print(f"    🔍 Checking {len(old_lines)} lines individually:")
                        for j, old_line in enumerate(old_lines):
                            if old_line.strip() in file_content:
                                print(f"      Line {j+1}: ✅ Found")
                            else:
                                print(f"      Line {j+1}: ❌ Not found - {repr(old_line)}")
                
                # Extract NEW_CODE
                new_code_match = re.search(
                    r"NEW_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
                )
                if new_code_match:
                    new_code = new_code_match.group(1)
                    print(f"  NEW_CODE: {len(new_code)} chars")
                
                modifications.append({
                    'file': file_path_extracted if file_match else 'N/A',
                    'description': description if desc_match else 'N/A',
                    'old_code': old_code if old_code_match else 'N/A',
                    'new_code': new_code if new_code_match else 'N/A'
                })
                
            except Exception as e:
                print(f"  ❌ Error parsing block {i}: {e}")
        
        print(f"\n📊 Parsing Summary:")
        print(f"  Total modifications parsed: {len(modifications)}")
        
        for i, mod in enumerate(modifications, 1):
            print(f"  Modification {i}:")
            print(f"    File: {mod['file']}")
            print(f"    Description: {mod['description'][:50]}...")
            
            if mod['old_code'] != 'N/A':
                old_code_in_file = mod['old_code'].strip() in file_content
                print(f"    OLD_CODE in file: {'✅' if old_code_in_file else '❌'}")
                
                if not old_code_in_file:
                    print(f"    🔍 Debugging why OLD_CODE not found...")
                    
                    # Check for partial matches
                    old_lines = mod['old_code'].split('\n')
                    for j, line in enumerate(old_lines):
                        line_stripped = line.strip()
                        if line_stripped and line_stripped in file_content:
                            # Find where this line appears
                            file_lines = file_content.splitlines()
                            for k, file_line in enumerate(file_lines):
                                if line_stripped in file_line:
                                    print(f"      Line {j+1} found at file line {k+1}: {repr(file_line)}")
                                    break
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_jwt_secret_already_exists():
    """Check if JWT_SECRET already exists in the file"""
    print("\n🔍 Checking JWT_SECRET Existence")
    print("=" * 40)
    
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        lines = file_content.splitlines()
        
        jwt_related_lines = []
        for i, line in enumerate(lines, 1):
            if 'JWT' in line.upper():
                jwt_related_lines.append((i, line))
        
        print(f"📋 JWT-related lines found:")
        for line_num, line in jwt_related_lines:
            print(f"  Line {line_num}: {line}")
        
        if any('JWT_SECRET' in line for _, line in jwt_related_lines):
            print(f"⚠️ JWT_SECRET already exists in the file!")
            print(f"💡 Agent should UPDATE existing value, not ADD new one")
            return True
        else:
            print(f"✅ JWT_SECRET not found - safe to add")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all debug tests"""
    print("🚀 Debugging .env.example Modification Issue")
    print("=" * 70)
    
    jwt_exists = check_jwt_secret_already_exists()
    debug_success = debug_env_modification()
    
    print("\n" + "=" * 70)
    print(f"📊 Debug Results:")
    print(f"   JWT_SECRET already exists: {'⚠️ YES' if jwt_exists else '✅ NO'}")
    print(f"   Debug analysis: {'✅ SUCCESS' if debug_success else '❌ FAILED'}")
    
    if jwt_exists:
        print("🎯 Root Cause: Agent trying to add JWT_SECRET that already exists")
        print("💡 Solution: Planner should detect existing variables and plan UPDATE instead of ADD")
    else:
        print("🔍 Need deeper investigation - JWT_SECRET doesn't exist but modification still fails")


if __name__ == "__main__":
    main()
