"""
Test insertion point logic directly
"""

def _find_best_insertion_point(content: str) -> dict | None:
    """
    Find the best insertion point in file content using line-by-line analysis.
    
    Args:
        content: File content to analyze
        
    Returns:
        Dict with insertion point info or None if not found
    """
    lines = content.split('\n')
    
    # Priority order for insertion points
    insertion_patterns = [
        {"pattern": "pass", "type": "pass"},
        {"pattern": "# TODO: Implement", "type": "todo_implement"},
        {"pattern": "# TODO", "type": "todo"},
        {"pattern": "...", "type": "ellipsis"},
        {"pattern": "# Add implementation here", "type": "add_implementation"},
        {"pattern": "# Implementation goes here", "type": "implementation_here"},
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        for pattern_info in insertion_patterns:
            pattern = pattern_info["pattern"]
            
            # Check for exact match or standalone keyword
            if pattern == "pass":
                # For 'pass', check if it's a standalone statement
                if stripped == "pass" or (stripped.startswith("pass ") and "#" in stripped):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern
                    }
            elif pattern == "...":
                # For ellipsis, check if it's standalone
                if stripped == "..." or stripped.startswith("... "):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern
                    }
            else:
                # For comment patterns, check if line contains the pattern
                if pattern in stripped:
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern
                    }
    
    return None


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


def test_real_files():
    """Test với real files."""
    print("\n🧪 Testing with real demo files...")
    
    from pathlib import Path
    
    # Test với file user.py (có substring pass nhưng không có standalone pass)
    user_model_path = "app/agents/demo/app/models/user.py"
    if Path(user_model_path).exists():
        content = Path(user_model_path).read_text()
        print(f"📄 Analyzing {user_model_path}")
        result = _find_best_insertion_point(content)
        if result:
            print(f"   ❌ Found: {result['type']} at line {result['line']} (should be None)")
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
            print(f"   ❌ Found: {result['type']} at line {result['line']} (should be None)")
            print(f"   📝 Original line: '{result['original_line']}'")
        else:
            print("   ✅ No insertion point found (correct - file is complete)")


def main():
    """Run tests."""
    print("🚀 Testing Improved Insertion Point Logic...\n")
    
    test_insertion_point_detection()
    test_real_files()
    
    print("\n🏁 Tests Completed!")


if __name__ == "__main__":
    main()
