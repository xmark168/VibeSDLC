#!/usr/bin/env python3
"""
Debug script để phân tích lỗi modification #2 trong .env.example file.
"""

import sys
import os
import re

# Add path để import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-agent-service', 'app'))

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


def simulate_parse_modifications(llm_output_sample):
    """Simulate parsing modifications từ LLM output."""
    print("🧪 Simulating parse_structured_modifications...")
    
    modifications = []
    
    # Split by MODIFICATION markers
    modification_blocks = re.split(r"MODIFICATION #\d+:", llm_output_sample)
    print(f"📊 Found {len(modification_blocks)} blocks (including empty first)")
    
    for i, block in enumerate(modification_blocks[1:], 1):  # Skip first empty block
        print(f"\n🔍 Processing block {i}:")
        print(f"Block content length: {len(block)} chars")
        print(f"Block preview: {repr(block[:100])}...")
        
        try:
            # Extract file path
            file_match = re.search(r"FILE:\s*(.+)", block)
            if not file_match:
                print(f"❌ No FILE found in block {i}")
                continue
            file_path = file_match.group(1).strip()
            print(f"✅ FILE: {file_path}")

            # Extract description
            desc_match = re.search(r"DESCRIPTION:\s*(.+)", block)
            if not desc_match:
                print(f"❌ No DESCRIPTION found in block {i}")
                continue
            description = desc_match.group(1).strip()
            print(f"✅ DESCRIPTION: {description}")

            # Extract OLD_CODE
            old_code_match = re.search(
                r"OLD_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
            )
            if not old_code_match:
                print(f"❌ No OLD_CODE found in block {i}")
                continue
            old_code = old_code_match.group(1)
            print(f"✅ OLD_CODE found ({len(old_code)} chars):")
            print(f"   Raw: {repr(old_code)}")
            print(f"   Display: {old_code}")

            # Extract NEW_CODE
            new_code_match = re.search(
                r"NEW_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
            )
            if not new_code_match:
                print(f"❌ No NEW_CODE found in block {i}")
                continue
            new_code = new_code_match.group(1)
            print(f"✅ NEW_CODE found ({len(new_code)} chars)")

            # Store modification info
            modification = {
                'file_path': file_path,
                'old_code': old_code,
                'new_code': new_code,
                'description': description,
                'block_index': i
            }
            modifications.append(modification)
            print(f"✅ Modification {i} parsed successfully")

        except Exception as e:
            print(f"❌ Error parsing block {i}: {e}")
            continue

    return modifications


def test_old_code_in_file(old_code, file_content):
    """Test if OLD_CODE exists in file content."""
    print(f"\n🔍 Testing OLD_CODE in file...")
    print(f"OLD_CODE length: {len(old_code)} chars")
    print(f"File content length: {len(file_content)} chars")
    
    # Test exact match
    found = old_code in file_content
    print(f"✅ Exact match found: {found}")
    
    if not found:
        print("\n🔍 Debugging why not found...")
        
        # Test stripped version
        old_code_stripped = old_code.strip()
        found_stripped = old_code_stripped in file_content
        print(f"✅ Stripped match found: {found_stripped}")
        
        # Test line by line
        if '\n' in old_code:
            old_lines = old_code.split('\n')
            print(f"📄 OLD_CODE has {len(old_lines)} lines:")
            for i, line in enumerate(old_lines):
                print(f"  Line {i+1}: {repr(line)}")
                line_found = line in file_content
                print(f"    Found in file: {line_found}")
        
        # Show file content around potential matches
        if old_code_stripped:
            first_line = old_code_stripped.split('\n')[0] if '\n' in old_code_stripped else old_code_stripped
            if first_line in file_content:
                print(f"\n📄 First line found in file. Context:")
                lines = file_content.splitlines()
                for i, line in enumerate(lines):
                    if first_line.strip() in line:
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        print(f"  Context around line {i+1}:")
                        for j in range(start, end):
                            marker = ">>>" if j == i else "   "
                            print(f"  {marker} {j+1}: {repr(lines[j])}")
    
    return found


def main():
    """Main debug function."""
    print("🚀 Starting .env.example modification debug...\n")
    
    # Read file content
    file_content = read_env_file()
    if not file_content:
        return False
    
    print(f"📄 File content loaded: {len(file_content)} chars")
    print(f"📄 File lines: {len(file_content.splitlines())}")
    
    # Sample LLM output that might cause the issue
    # This simulates what the agent might be trying to parse
    sample_llm_output = """
MODIFICATION #1:
FILE: .env.example
DESCRIPTION: Update database configuration

OLD_CODE:
```
# Database
MONGODB_URI=mongodb://localhost:27017/express_basic
```

NEW_CODE:
```
# Database Configuration
MONGODB_URI=mongodb://localhost:27017/express_basic
DB_NAME=express_basic
```

MODIFICATION #2:
FILE: .env.example
DESCRIPTION: Add Redis configuration

OLD_CODE:
```
# Redis
REDIS_URL=redis://localhost:6379
```

NEW_CODE:
```
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=
```
"""
    
    # Parse modifications
    modifications = simulate_parse_modifications(sample_llm_output)
    
    print(f"\n📊 Parsed {len(modifications)} modifications")
    
    # Test each modification
    for i, mod in enumerate(modifications, 1):
        print(f"\n{'='*50}")
        print(f"🧪 Testing Modification #{i}")
        print(f"File: {mod['file_path']}")
        print(f"Description: {mod['description']}")
        
        # Test OLD_CODE
        found = test_old_code_in_file(mod['old_code'], file_content)
        
        if found:
            print(f"✅ Modification #{i} OLD_CODE validation would PASS")
        else:
            print(f"❌ Modification #{i} OLD_CODE validation would FAIL")
            print("💡 This explains why modification #2 might be failing!")
    
    return True


if __name__ == "__main__":
    success = main()
    print(f"\n🏁 Debug result: {'COMPLETED' if success else 'FAILED'}")
