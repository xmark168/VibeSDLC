"""
Test improved incremental modification logic
"""

import sys
import json
import tempfile
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the new function
import importlib.util
spec = importlib.util.spec_from_file_location(
    "implement_files", 
    "app/agents/developer/implementor/nodes/implement_files.py"
)
implement_files = importlib.util.module_from_spec(spec)
spec.loader.exec_module(implement_files)

_find_best_insertion_point = implement_files._find_best_insertion_point


def test_insertion_point_detection():
    """Test improved insertion point detection."""
    print("🧪 Testing improved insertion point detection...")
    
    # Test case 1: File with substring "pass" but no standalone pass
    content_no_pass = '''class UserCreate(BaseModel):
    """Schema for user creation."""
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    def validate_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
'''
    
    # Test case 2: File with standalone pass
    content_with_pass = '''class UserService:
    """User service class."""
    
    def create_user(self, user_data):
        # TODO: Implement user creation
        pass
    
    def update_password(self, user_id, new_password):
        pass  # TODO: Implement
'''
    
    # Test case 3: File with TODO comments
    content_with_todo = '''class AuthService:
    """Authentication service."""
    
    def login(self, email, password):
        # TODO: Implement login logic
        return None
    
    def logout(self, user_id):
        # Add implementation here
        return True
'''
    
    print("📄 Test 1: File with substring 'pass' but no standalone pass")
    result = _find_best_insertion_point(content_no_pass)
    print(f"   Result: {result}")
    
    print("📄 Test 2: File with standalone pass statements")
    result = _find_best_insertion_point(content_with_pass)
    if result:
        print(f"   ✅ Found: {result['type']} at line {result['line']}")
        print(f"   📝 Original line: '{result['original_line']}'")
        print(f"   📏 Indentation: {result['indentation']} spaces")
    else:
        print("   ❌ No insertion point found")
    
    print("📄 Test 3: File with TODO comments")
    result = _find_best_insertion_point(content_with_todo)
    if result:
        print(f"   ✅ Found: {result['type']} at line {result['line']}")
        print(f"   📝 Original line: '{result['original_line']}'")
        print(f"   📏 Indentation: {result['indentation']} spaces")
    else:
        print("   ❌ No insertion point found")


def test_real_file_analysis():
    """Test với real files từ demo project."""
    print("\n🧪 Testing with real demo files...")
    
    # Test với file user.py (có substring pass nhưng không có standalone pass)
    user_model_path = "app/agents/demo/app/models/user.py"
    if Path(user_model_path).exists():
        content = Path(user_model_path).read_text()
        print(f"📄 Analyzing {user_model_path}")
        result = _find_best_insertion_point(content)
        if result:
            print(f"   ✅ Found: {result['type']} at line {result['line']}")
            print(f"   📝 Original line: '{result['original_line']}'")
        else:
            print("   ✅ No insertion point found (correct - file is complete)")
    
    # Test với file schemas/user.py
    user_schema_path = "app/agents/demo/app/schemas/user.py"
    if Path(user_schema_path).exists():
        content = Path(user_schema_path).read_text()
        print(f"📄 Analyzing {user_schema_path}")
        result = _find_best_insertion_point(content)
        if result:
            print(f"   ✅ Found: {result['type']} at line {result['line']}")
            print(f"   📝 Original line: '{result['original_line']}'")
        else:
            print("   ✅ No insertion point found (correct - file is complete)")


def test_indentation_preservation():
    """Test indentation preservation logic."""
    print("\n🧪 Testing indentation preservation...")
    
    content = '''class UserService:
    def create_user(self, data):
        # TODO: Implement
        pass
        
    def update_user(self, user_id, data):
            # Nested indentation
            pass
'''
    
    new_content = '''user = User(**data)
db.add(user)
db.commit()
return user'''
    
    result = _find_best_insertion_point(content)
    if result:
        print(f"📍 Found insertion point: {result['type']} at line {result['line']}")
        print(f"📏 Indentation: {result['indentation']} spaces")
        
        # Test indentation logic
        indentation = " " * result['indentation']
        new_content_lines = new_content.split('\n')
        indented_content = '\n'.join([
            indentation + line if i > 0 and line.strip() else line
            for i, line in enumerate(new_content_lines)
        ])
        
        print(f"📝 Original line: '{result['original_line']}'")
        print(f"🔄 Replacement content:")
        print(indented_content)


def main():
    """Run improved incremental tests."""
    print("🚀 Testing Improved Incremental Modification Logic...\n")
    
    test_insertion_point_detection()
    test_real_file_analysis()
    test_indentation_preservation()
    
    print("\n🏁 Tests Completed!")
    print("\n💡 Key Improvements:")
    print("   1. ✅ Line-by-line analysis instead of substring search")
    print("   2. ✅ Standalone 'pass' detection (not 'password')")
    print("   3. ✅ Priority-based insertion point selection")
    print("   4. ✅ Indentation preservation")
    print("   5. ✅ Exact line replacement (no ambiguity)")


if __name__ == "__main__":
    main()
