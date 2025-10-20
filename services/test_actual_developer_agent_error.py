#!/usr/bin/env python3
"""
Test script để run actual Developer Agent workflow và capture exact error
"""

import os
import sys
import traceback

# Add the path to import modules
sys.path.append('ai-agent-service/app/agents/developer/implementor/utils')
sys.path.append('ai-agent-service/app/agents/developer/implementor/nodes')
sys.path.append('ai-agent-service/app/agents/developer/implementor')

def test_actual_generate_code_error():
    """Test actual generate_code function với real parameters"""
    
    print("🔍 Testing Actual Generate Code Error")
    print("=" * 60)
    
    try:
        # Import required modules
        from generate_code import _generate_file_modification
        from state import FileChange
        
        # Create FileChange object similar to actual usage
        file_change = FileChange(
            file_path="src/app.js",
            change_type="incremental",
            description="Add login endpoint to Express.js application"
        )
        
        # Set up parameters similar to actual usage
        codebase_context = "Express.js backend application with authentication routes"
        working_dir = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        tech_stack = "express"
        
        print(f"🧪 Testing _generate_file_modification with:")
        print(f"   📄 File: {file_change.file_path}")
        print(f"   🔧 Change type: {file_change.change_type}")
        print(f"   📝 Description: {file_change.description}")
        print(f"   🏗️ Tech stack: {tech_stack}")
        print(f"   📁 Working dir: {working_dir}")
        
        # Call the actual function
        print("\n🚀 Calling _generate_file_modification...")
        result = _generate_file_modification(
            file_change=file_change,
            codebase_context=codebase_context,
            working_dir=working_dir,
            tech_stack=tech_stack
        )
        
        print(f"\n✅ Function completed successfully")
        print(f"   📊 Result type: {type(result)}")
        print(f"   📄 Result: {result}")
        
        return "SUCCESS"
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print(f"   🔍 Error type: {type(e)}")
        print(f"   🔍 Error string: {repr(str(e))}")
        
        # Check if this is the exact error we're looking for
        if str(e) == '\n  // existing register logic\n':
            print("   🎯 FOUND EXACT ERROR MATCH!")
            
        # Print full traceback
        print("\n📊 Full traceback:")
        traceback.print_exc()
        
        return f"ERROR: {e}"

def test_actual_implement_files_error():
    """Test actual implement_files workflow"""
    
    print("\n🔍 Testing Actual Implement Files Error")
    print("=" * 60)
    
    try:
        # Import required modules
        from implement_files import _apply_structured_modifications
        from state import FileChange
        
        # Create FileChange with structured modifications (simulating LLM output)
        file_change = FileChange(
            file_path="src/app.js",
            change_type="incremental",
            description="Add login endpoint"
        )
        
        # Simulate LLM response với placeholder OLD_CODE
        file_change.structured_modifications = """
MODIFICATION #1:
FILE: src/app.js
DESCRIPTION: Add login endpoint

OLD_CODE:
  // existing register logic

NEW_CODE:
```javascript
router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    
    if (!email || !password) {
        return res.status(400).json({ message: 'Email and password are required.' });
    }
    
    try {
        const user = await User.findOne({ email });
        if (!user) {
            return res.status(401).json({ message: 'Invalid email or password.' });
        }
        
        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) {
            return res.status(401).json({ message: 'Invalid email or password.' });
        }
        
        const token = jwt.sign(
            { id: user._id, email: user.email },
            process.env.JWT_SECRET,
            { expiresIn: '1h' }
        );
        
        res.status(200).json({ token });
    } catch (error) {
        console.error(error);
        res.status(500).json({ message: 'Internal server error.' });
    }
});

  // existing register logic
```
"""
        
        working_dir = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        
        print(f"🧪 Testing _apply_structured_modifications with:")
        print(f"   📄 File: {file_change.file_path}")
        print(f"   📝 Structured modifications length: {len(file_change.structured_modifications)} chars")
        print(f"   📁 Working dir: {working_dir}")
        
        # Call the actual function
        print("\n🚀 Calling _apply_structured_modifications...")
        result = _apply_structured_modifications(
            file_change=file_change,
            working_dir=working_dir
        )
        
        print(f"\n✅ Function completed")
        print(f"   📊 Result: {result}")
        
        return "SUCCESS"
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print(f"   🔍 Error type: {type(e)}")
        print(f"   🔍 Error string: {repr(str(e))}")
        
        # Check if this is the exact error we're looking for
        if str(e) == '\n  // existing register logic\n':
            print("   🎯 FOUND EXACT ERROR MATCH!")
            
        # Print full traceback
        print("\n📊 Full traceback:")
        traceback.print_exc()
        
        return f"ERROR: {e}"

def test_check_file_exists():
    """Check if target file exists"""
    
    print("\n🔍 Checking Target File")
    print("=" * 60)
    
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/app.js"
    
    if os.path.exists(file_path):
        print(f"✅ File exists: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"   📊 File size: {len(content)} chars")
        print(f"   📊 Line count: {content.count(chr(10)) + 1}")
        print(f"   📄 First 200 chars: {content[:200]}...")
        print(f"   📄 Last 200 chars: ...{content[-200:]}")
        
        return True
    else:
        print(f"❌ File not found: {file_path}")
        return False

def test_import_modules():
    """Test importing required modules"""
    
    print("\n🔍 Testing Module Imports")
    print("=" * 60)
    
    modules_to_test = [
        ('generate_code', '_generate_file_modification'),
        ('implement_files', '_apply_structured_modifications'),
        ('state', 'FileChange'),
        ('incremental_modifications', 'parse_structured_modifications'),
    ]
    
    results = {}
    
    for module_name, item_name in modules_to_test:
        try:
            module = __import__(module_name)
            if hasattr(module, item_name):
                print(f"   ✅ {module_name}.{item_name} - OK")
                results[f"{module_name}.{item_name}"] = "OK"
            else:
                print(f"   ❌ {module_name}.{item_name} - Missing attribute")
                results[f"{module_name}.{item_name}"] = "Missing attribute"
        except ImportError as e:
            print(f"   ❌ {module_name} - Import error: {e}")
            results[module_name] = f"Import error: {e}"
        except Exception as e:
            print(f"   ❌ {module_name} - Error: {e}")
            results[module_name] = f"Error: {e}"
    
    return results

def main():
    """Main test function"""
    
    print("🚀 Actual Developer Agent Error Test")
    print("=" * 80)
    
    # Test 1: Check imports
    import_results = test_import_modules()
    
    # Test 2: Check file exists
    file_exists = test_check_file_exists()
    
    # Test 3: Test actual functions if imports work
    if all("OK" in str(result) for result in import_results.values()) and file_exists:
        print("\n🎯 All prerequisites met, testing actual functions...")
        
        # Test generate_code function
        generate_result = test_actual_generate_code_error()
        
        # Test implement_files function
        implement_result = test_actual_implement_files_error()
        
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        print(f"   Import tests: {import_results}")
        print(f"   File exists: {file_exists}")
        print(f"   Generate code test: {generate_result}")
        print(f"   Implement files test: {implement_result}")
        
        # Analysis
        if "EXACT ERROR MATCH" in str(generate_result) or "EXACT ERROR MATCH" in str(implement_result):
            print("\n🎯 FOUND EXACT ERROR SOURCE!")
            if "EXACT ERROR MATCH" in str(generate_result):
                print("   📍 Error source: _generate_file_modification function")
            if "EXACT ERROR MATCH" in str(implement_result):
                print("   📍 Error source: _apply_structured_modifications function")
        else:
            print("\n❓ Error source not identified in these tests")
            print("   💡 May need to test other functions or check different scenarios")
    
    else:
        print("\n❌ Prerequisites not met:")
        print(f"   Import results: {import_results}")
        print(f"   File exists: {file_exists}")
        print("   Cannot proceed with function tests")
    
    print("\n💡 Next Steps:")
    print("   1. If error found: Fix the identified source")
    print("   2. If error not found: Check other functions in call stack")
    print("   3. Run actual Developer Agent to capture real error with enhanced logging")

if __name__ == "__main__":
    main()
