#!/usr/bin/env python3
"""
Debug script to test the actual validation logic with the exact same parameters.
"""

import sys
import os

# Add the ai-agent-service to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-agent-service'))


def test_actual_validation():
    """Test the actual validation logic with exact same parameters"""
    print("🔍 Testing Actual Validation Logic")
    print("=" * 50)
    
    try:
        # Import the actual classes
        from app.agents.developer.implementor.utils.incremental_modifications import (
            CodeModification,
            IncrementalModificationValidator,
            validate_modifications_batch
        )
        
        print("✅ Successfully imported validation classes")
        
        # Read the actual file content
        file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"✅ Read file: {len(file_content)} chars")
        
        # Create the exact same modification that's failing
        modification = CodeModification(
            file_path="src/services/authService.js",
            old_code="""    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;""",
            new_code="""    // Remove the password field from the returned user object
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
    };""",
            description="Add functionality to generate a JWT token upon successful registration."
        )
        
        print("✅ Created CodeModification object")
        print(f"   File: {modification.file_path}")
        print(f"   OLD_CODE length: {len(modification.old_code)} chars")
        print(f"   NEW_CODE length: {len(modification.new_code)} chars")
        
        # Test individual validation
        print("\n🔍 Testing individual modification validation...")
        validator = IncrementalModificationValidator(file_content)
        is_valid, error_message = validator.validate_modification(modification)
        
        print(f"Result: {is_valid}")
        if not is_valid:
            print(f"Error: {error_message}")
        else:
            print("✅ Individual validation PASSED")
        
        # Test batch validation
        print("\n🔍 Testing batch validation...")
        modifications = [modification]
        batch_valid, batch_errors = validate_modifications_batch(file_content, modifications)
        
        print(f"Batch result: {batch_valid}")
        if not batch_valid:
            print(f"Batch errors:")
            for error in batch_errors:
                print(f"  - {error}")
        else:
            print("✅ Batch validation PASSED")
        
        # If validation fails, let's debug step by step
        if not is_valid or not batch_valid:
            print("\n🔍 Step-by-step debugging...")
            
            old_code = modification.old_code.strip()
            print(f"OLD_CODE (stripped): {repr(old_code[:100])}...")
            
            # Test substring
            if old_code in file_content:
                print("✅ Substring check PASSED")
            else:
                print("❌ Substring check FAILED")
                return False
            
            # Test uniqueness
            count = file_content.count(old_code)
            print(f"OLD_CODE appears {count} times in file")
            
            if count == 0:
                print("❌ Count is 0 - this shouldn't happen!")
                return False
            elif count > 1:
                print("❌ OLD_CODE appears multiple times")
                return False
            
            # Test line boundaries
            if "\n" in old_code:
                print("🔍 Testing line boundaries...")
                file_lines = file_content.splitlines()
                old_lines = old_code.split("\n")
                
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
                
                if found_start == -1:
                    print("❌ Line boundaries check FAILED")
                    
                    # Debug line by line
                    print("\n🔍 Line-by-line comparison:")
                    for i, old_line in enumerate(old_lines):
                        print(f"Expected line {i + 1}: {repr(old_line)}")
                        
                        # Find similar lines in file
                        for j, file_line in enumerate(file_lines):
                            if old_line == file_line:
                                print(f"  ✅ Exact match at file line {j + 1}")
                                break
                            elif old_line.strip() == file_line.strip():
                                print(f"  ⚠️ Content match (whitespace diff) at file line {j + 1}")
                                print(f"     File line: {repr(file_line)}")
                                break
                        else:
                            print(f"  ❌ No match found")
                    
                    return False
                else:
                    print(f"✅ Line boundaries check PASSED (start at line {found_start + 1})")
        
        return is_valid and batch_valid
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 This might be due to missing dependencies")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the actual validation test"""
    print("🚀 Testing Actual Validation Logic")
    print("=" * 60)
    
    success = test_actual_validation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Validation logic works correctly - issue might be elsewhere")
    else:
        print("❌ Validation logic has issues - this explains the error")


if __name__ == "__main__":
    main()
