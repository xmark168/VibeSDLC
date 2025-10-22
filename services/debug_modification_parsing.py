#!/usr/bin/env python3
"""
Debug script to analyze how structured modifications are parsed.
"""

import re
import sys
import os

# Add the ai-agent-service to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-agent-service'))


def debug_modification_parsing():
    """Debug how the modification is parsed from LLM output"""
    print("🔍 Debugging Modification Parsing")
    print("=" * 50)
    
    # Simulate the LLM output that caused the error
    # Based on the error log, this is what the agent received
    llm_output = """MODIFICATION #1:
FILE: src/services/authService.js
DESCRIPTION: Add functionality to generate a JWT token upon successful registration.

OLD_CODE:
```javascript
    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;
```

NEW_CODE:
```javascript
    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    // Generate JWT token
    const token = jwt.sign(
      { userId: savedUser._id, email: savedUser.email },
      process.env.JWT_SECRET,
      { expiresIn: '24h' }
    );

    return {
      user: userWithoutPassword,
      token
    };
```"""
    
    print("📋 Simulated LLM Output:")
    print("-" * 30)
    print(llm_output)
    
    # Now simulate the exact parsing logic
    print("\n🔍 Simulating parse_structured_modifications...")
    
    # Split by MODIFICATION markers
    modification_blocks = re.split(r"MODIFICATION #\d+:", llm_output)
    print(f"📊 Found {len(modification_blocks)} blocks (including empty first)")
    
    for i, block in enumerate(modification_blocks):
        print(f"\nBlock {i}:")
        print(f"  Length: {len(block)} chars")
        if block.strip():
            print(f"  First 100 chars: {repr(block[:100])}")
    
    # Process the actual modification block
    if len(modification_blocks) > 1:
        block = modification_blocks[1]  # Skip first empty block
        
        print(f"\n🔍 Processing modification block:")
        print(f"Block content: {repr(block[:200])}...")
        
        # Extract file path
        file_match = re.search(r"FILE:\s*(.+)", block)
        if file_match:
            file_path = file_match.group(1).strip()
            print(f"✅ File path: {repr(file_path)}")
        else:
            print("❌ No file path found")
            return False
        
        # Extract description
        desc_match = re.search(r"DESCRIPTION:\s*(.+)", block)
        if desc_match:
            description = desc_match.group(1).strip()
            print(f"✅ Description: {repr(description)}")
        else:
            print("❌ No description found")
            return False
        
        # Extract OLD_CODE - this is the critical part
        old_code_match = re.search(
            r"OLD_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
        )
        if old_code_match:
            old_code = old_code_match.group(1)
            print(f"✅ OLD_CODE extracted:")
            print(f"   Raw: {repr(old_code)}")
            print(f"   Length: {len(old_code)} chars")
            
            # Split into lines to see the structure
            old_lines = old_code.split('\n')
            print(f"   Lines: {len(old_lines)}")
            for j, line in enumerate(old_lines):
                print(f"     Line {j + 1}: {repr(line)}")
        else:
            print("❌ No OLD_CODE found")
            return False
        
        # Extract NEW_CODE
        new_code_match = re.search(
            r"NEW_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
        )
        if new_code_match:
            new_code = new_code_match.group(1)
            print(f"✅ NEW_CODE extracted:")
            print(f"   Length: {len(new_code)} chars")
            print(f"   First 100 chars: {repr(new_code[:100])}")
        else:
            print("❌ No NEW_CODE found")
            return False
        
        # Now test this OLD_CODE against the actual file
        print(f"\n🔍 Testing extracted OLD_CODE against actual file...")
        
        file_path_full = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
        
        try:
            with open(file_path_full, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            print(f"✅ Read file: {len(file_content)} chars")
            
            # Test substring match
            if old_code in file_content:
                print("✅ OLD_CODE found in file (substring match)")
            else:
                print("❌ OLD_CODE NOT found in file (substring match)")
                
                # Let's see what's different
                print("\n🔍 Analyzing differences...")
                
                # Check if it's a whitespace issue
                old_code_normalized = old_code.strip()
                file_content_normalized = file_content.strip()
                
                if old_code_normalized in file_content_normalized:
                    print("✅ OLD_CODE found after stripping whitespace")
                else:
                    print("❌ OLD_CODE still not found after stripping")
                    
                    # Check line by line
                    old_lines = old_code.split('\n')
                    file_lines = file_content.split('\n')
                    
                    print(f"\n🔍 Line-by-line analysis:")
                    for i, old_line in enumerate(old_lines):
                        found_in_file = False
                        for j, file_line in enumerate(file_lines):
                            if old_line.strip() and old_line.strip() in file_line:
                                print(f"   Line {i + 1}: Found at file line {j + 1}")
                                print(f"      Expected: {repr(old_line)}")
                                print(f"      File    : {repr(file_line)}")
                                found_in_file = True
                                break
                        
                        if not found_in_file and old_line.strip():
                            print(f"   Line {i + 1}: NOT FOUND")
                            print(f"      Expected: {repr(old_line)}")
            
            # Test line boundaries
            print(f"\n🔍 Testing line boundaries...")
            file_lines = file_content.splitlines()
            old_lines = old_code.split('\n')
            
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
                print(f"✅ Line boundaries match starting at line {found_start + 1}")
            else:
                print(f"❌ Line boundaries don't match")
            
            return found_start != -1
            
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return False
    
    return False


def main():
    """Run the debug analysis"""
    print("🚀 Debugging Modification Parsing Issue")
    print("=" * 60)
    
    success = debug_modification_parsing()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Modification parsing should work correctly")
    else:
        print("❌ Modification parsing has issues - need to investigate further")


if __name__ == "__main__":
    main()
