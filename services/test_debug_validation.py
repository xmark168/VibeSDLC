#!/usr/bin/env python3
"""
Test script to trigger the exact validation scenario with debug output.
"""

import sys
import os

# Add the path to import the validation modules
sys.path.append('ai-agent-service/app/agents/developer/implementor/utils')

try:
    from incremental_modifications import (
        validate_modifications_batch,
        parse_structured_modifications,
        CodeModification
    )
    
    def test_with_debug_output():
        """Test the validation with debug output"""
        print("🔍 Testing Validation with Debug Output")
        print("=" * 60)
        
        # Read the actual file content
        file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            print(f"✅ Read file: {len(file_content)} chars")
            
            # Create the exact modifications that are failing
            modifications = [
                CodeModification(
                    file_path=".env.example",
                    old_code="""# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRE=1h
JWT_REFRESH_EXPIRE=7d
BCRYPT_ROUNDS=12""",
                    new_code="""# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRE=1h
JWT_REFRESH_EXPIRE=7d
BCRYPT_ROUNDS=12""",
                    description="Add JWT_SECRET variable"
                ),
                CodeModification(
                    file_path=".env.example",
                    old_code="""# Database
MONGODB_URI=mongodb://localhost:27017/express_basic

# Redis
REDIS_URL=redis://localhost:6379""",
                    new_code="""# Database
MONGODB_URI=mongodb://localhost:27017/express_basic

# Redis
REDIS_URL=redis://localhost:6379

# Additional JWT Configuration
JWT_ALGORITHM=HS256
JWT_ISSUER=express-basic-app""",
                    description="Add additional JWT configuration"
                )
            ]
            
            print(f"\n📋 Testing with {len(modifications)} modifications")
            
            # Call the validation function with debug output
            print(f"\n🔍 Calling validate_modifications_batch...")
            is_valid, errors = validate_modifications_batch(file_content, modifications)
            
            print(f"\n📊 Validation Results:")
            print(f"   Valid: {is_valid}")
            print(f"   Errors: {len(errors)}")
            
            if errors:
                print(f"   Error details:")
                for i, error in enumerate(errors, 1):
                    print(f"     {i}. {error}")
            
            return is_valid
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_parsing_with_debug():
        """Test the parsing with debug output"""
        print("\n🔍 Testing Parsing with Debug Output")
        print("=" * 60)
        
        # Simulate the LLM output that's causing issues
        llm_output = """MODIFICATION #1:
FILE: .env.example
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
FILE: .env.example
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
        
        print(f"📋 Parsing LLM output ({len(llm_output)} chars)...")
        
        try:
            modifications = parse_structured_modifications(llm_output)
            print(f"✅ Parsed {len(modifications)} modifications")
            
            for i, mod in enumerate(modifications, 1):
                print(f"\n📋 Modification {i}:")
                print(f"   File: {mod.file_path}")
                print(f"   Description: {mod.description}")
                print(f"   OLD_CODE: {len(mod.old_code)} chars")
                print(f"   NEW_CODE: {len(mod.new_code)} chars")
            
            return modifications
            
        except Exception as e:
            print(f"❌ Parsing error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def main():
        """Run all tests"""
        print("🚀 Testing Debug Validation")
        print("=" * 70)
        
        # Test parsing first
        parsed_mods = test_parsing_with_debug()
        
        if parsed_mods:
            print(f"\n✅ Parsing successful, testing validation...")
            
            # Read file content
            file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/.env.example"
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Test validation with parsed modifications
            print(f"\n🔍 Testing validation with parsed modifications...")
            is_valid, errors = validate_modifications_batch(file_content, parsed_mods)
            
            print(f"\n📊 Final Results:")
            print(f"   Parsing: ✅ SUCCESS")
            print(f"   Validation: {'✅ SUCCESS' if is_valid else '❌ FAILED'}")
            
            if not is_valid:
                print(f"   Errors:")
                for error in errors:
                    print(f"     - {error}")
        else:
            print(f"\n❌ Parsing failed, cannot test validation")
        
        # Also test with manual modifications
        validation_success = test_with_debug_output()
        
        print(f"\n" + "=" * 70)
        print(f"📊 Overall Results:")
        print(f"   Manual validation: {'✅ SUCCESS' if validation_success else '❌ FAILED'}")
        print(f"   Parsed validation: {'✅ SUCCESS' if parsed_mods and is_valid else '❌ FAILED'}")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Cannot import validation modules - they may have dependencies")
    print("🔍 This explains why the agent validation might behave differently")
