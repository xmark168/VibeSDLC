#!/usr/bin/env python3
"""
Debug script để test với real modification data từ implementor agent.
"""

import sys
import os

# Add path để import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-agent-service', 'app'))

try:
    from agents.developer.implementor.utils.incremental_modifications import (
        parse_structured_modifications,
        IncrementalModificationValidator,
        CodeModification
    )
    from agents.developer.implementor.nodes.implement_files import (
        _verify_file_content_for_modifications
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


def test_with_real_llm_output():
    """Test với real LLM output format."""
    print("🧪 Testing with realistic LLM output...")
    
    # Simulate real LLM output that might cause issues
    real_llm_output = """MODIFICATION #1:
FILE: .env.example
DESCRIPTION: Update database configuration section

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
DESCRIPTION: Add Redis configuration details

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
REDIS_DB=0
```"""

    file_content = read_env_file()
    if not file_content:
        return False
    
    print(f"📄 File content: {len(file_content)} chars")
    
    if IMPORTS_AVAILABLE:
        # Test với real parsing logic
        print("\n🔍 Testing with real parse_structured_modifications...")
        modifications = parse_structured_modifications(real_llm_output)
        print(f"📊 Parsed {len(modifications)} modifications")
        
        for i, mod in enumerate(modifications, 1):
            print(f"\n{'='*40}")
            print(f"🧪 Modification #{i}")
            print(f"File: {mod.file_path}")
            print(f"Description: {mod.description}")
            print(f"OLD_CODE ({len(mod.old_code)} chars): {repr(mod.old_code)}")
            
            # Test validation
            validator = IncrementalModificationValidator(file_content)
            is_valid, error_msg = validator.validate_modification(mod)
            
            print(f"✅ Validation result: {is_valid}")
            if not is_valid:
                print(f"❌ Error: {error_msg}")
            
            # Test file content verification
            print(f"\n🔍 Testing file content verification...")
            verification_result = _verify_file_content_for_modifications(
                mod.file_path, file_content, [mod]
            )
            
            print(f"✅ Verification result: {verification_result['valid']}")
            if not verification_result['valid']:
                print(f"❌ Reason: {verification_result['reason']}")
                if 'suggestions' in verification_result:
                    print(f"💡 Suggestions: {verification_result['suggestions']}")
    
    else:
        # Manual testing without imports
        print("\n🔍 Manual testing without imports...")
        
        # Test specific OLD_CODE patterns
        test_patterns = [
            "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic",
            "# Redis\nREDIS_URL=redis://localhost:6379"
        ]
        
        for i, pattern in enumerate(test_patterns, 1):
            print(f"\n🧪 Testing pattern #{i}:")
            print(f"Pattern: {repr(pattern)}")
            
            found = pattern in file_content
            print(f"✅ Found: {found}")
            
            if not found:
                print("🔍 Debugging...")
                
                # Test with different line endings
                pattern_crlf = pattern.replace('\n', '\r\n')
                found_crlf = pattern_crlf in file_content
                print(f"✅ Found with CRLF: {found_crlf}")
                
                # Test stripped
                pattern_stripped = pattern.strip()
                found_stripped = pattern_stripped in file_content
                print(f"✅ Found stripped: {found_stripped}")
                
                # Test individual lines
                lines = pattern.split('\n')
                print(f"📄 Testing {len(lines)} lines individually:")
                for j, line in enumerate(lines):
                    line_found = line in file_content
                    print(f"  Line {j+1} '{line}': {line_found}")
    
    return True


def test_whitespace_issues():
    """Test for whitespace and encoding issues."""
    print("\n🧪 Testing for whitespace and encoding issues...")
    
    file_content = read_env_file()
    if not file_content:
        return False
    
    # Analyze file content
    print(f"📄 File encoding analysis:")
    print(f"  Length: {len(file_content)} chars")
    print(f"  Lines: {len(file_content.splitlines())}")
    
    # Check line endings
    has_crlf = '\r\n' in file_content
    has_lf = '\n' in file_content and not has_crlf
    print(f"  Line endings: {'CRLF' if has_crlf else 'LF' if has_lf else 'Unknown'}")
    
    # Show specific lines around database section
    lines = file_content.splitlines()
    print(f"\n📄 Lines around database section:")
    for i, line in enumerate(lines[10:15], 11):
        print(f"  {i:2}: {repr(line)}")
    
    # Test exact matches
    database_section = "# Database\nMONGODB_URI=mongodb://localhost:27017/express_basic"
    redis_section = "# Redis\nREDIS_URL=redis://localhost:6379"
    
    print(f"\n🔍 Exact match tests:")
    print(f"  Database section: {database_section in file_content}")
    print(f"  Redis section: {redis_section in file_content}")
    
    return True


def main():
    """Main debug function."""
    print("🚀 Starting real modification debug...\n")
    
    try:
        test_with_real_llm_output()
        test_whitespace_issues()
        
        print("\n🎉 Debug completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    print(f"\n🏁 Debug result: {'COMPLETED' if success else 'FAILED'}")
