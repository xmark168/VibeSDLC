"""
Simple test to verify file extraction logic without dependencies.
"""

def _is_new_file(file_path, step):
    """
    Determine if a file should be created or modified based on path and step context.
    """
    # Check step action/description for creation keywords
    action = step.get("action", "").lower()
    description = step.get("description", "").lower()
    title = step.get("title", "").lower()
    
    creation_keywords = ["create", "add", "implement", "new", "generate", "build"]
    modification_keywords = ["update", "modify", "change", "edit", "integrate", "include"]
    
    # Check for explicit creation keywords
    for keyword in creation_keywords:
        if keyword in action or keyword in description or keyword in title:
            return True
    
    # Check for explicit modification keywords
    for keyword in modification_keywords:
        if keyword in action or keyword in description or keyword in title:
            return False
    
    # Default heuristics based on file type and common patterns
    if file_path.endswith(('.js', '.py', '.java', '.ts', '.go', '.rs')):
        # New source files are usually created
        if any(pattern in file_path for pattern in ['controller', 'service', 'model', 'route', 'middleware']):
            return True
    
    if file_path.endswith(('.test.js', '.test.py', '.spec.js', '.spec.py')):
        # Test files are usually created
        return True
    
    if file_path in ['app/main.py', 'app/main.js', 'main.py', 'main.js', 'requirements.txt', 'package.json']:
        # Main files and config files are usually modified
        return False
    
    # Default to creation for new files
    return True


def test_file_classification():
    """Test file classification logic."""
    
    print("🧪 Testing File Classification Logic")
    print("=" * 50)
    
    # Test cases from the JSON you provided
    test_cases = [
        {
            "file": "app/routes/auth.js",
            "step": {
                "title": "Create user registration endpoint",
                "description": "Implement the POST /api/auth/register endpoint to handle user registration.",
                "action": "Add a new route in the Express application."
            },
            "expected": "CREATE"
        },
        {
            "file": "app/middleware/validation.js",
            "step": {
                "title": "Implement input validation",
                "description": "Add validation logic for email format and password strength.",
                "action": "Use a validation library to enforce rules."
            },
            "expected": "CREATE"
        },
        {
            "file": "app/controllers/authController.js",
            "step": {
                "title": "Hash password before storing",
                "description": "Implement password hashing using bcrypt before saving user data.",
                "action": "Integrate bcrypt hashing in the registration logic."
            },
            "expected": "CREATE"  # First occurrence
        },
        {
            "file": "app/controllers/authController.js",
            "step": {
                "title": "Generate JWT token",
                "description": "Return a JWT token upon successful registration.",
                "action": "Integrate JWT generation in the registration response."
            },
            "expected": "MODIFY"  # Second occurrence - should be modify
        },
        {
            "file": "app/models/User.js",
            "step": {
                "title": "Store user data in MongoDB",
                "description": "Save the user data in the MongoDB database with a created_at timestamp.",
                "action": "Create a user model and save user data."
            },
            "expected": "CREATE"
        },
        {
            "file": "tests/unit/auth.test.js",
            "step": {
                "title": "Write unit tests for registration",
                "description": "Create comprehensive unit tests for the user registration functionality.",
                "action": "Add tests to ensure all scenarios are covered."
            },
            "expected": "CREATE"
        },
        {
            "file": "docs/api.md",
            "step": {
                "title": "Update API documentation",
                "description": "Document the new /api/auth/register endpoint in the API documentation.",
                "action": "Add details about the endpoint, request body, and response."
            },
            "expected": "MODIFY"  # Documentation updates are usually modifications
        }
    ]
    
    correct = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases):
        file_path = test_case["file"]
        step = test_case["step"]
        expected = test_case["expected"]
        
        is_create = _is_new_file(file_path, step)
        actual = "CREATE" if is_create else "MODIFY"
        
        status = "✅" if actual == expected else "❌"
        print(f"{status} Test {i+1}: {file_path}")
        print(f"    Step: {step['title']}")
        print(f"    Expected: {expected}, Actual: {actual}")
        
        if actual == expected:
            correct += 1
        else:
            print(f"    🔍 Action: '{step['action']}'")
            print(f"    🔍 Description: '{step['description']}'")
        
        print()
    
    print(f"📊 RESULTS: {correct}/{total} correct ({correct/total*100:.1f}%)")
    
    if correct == total:
        print("🎉 All tests passed! File classification logic is working correctly.")
    else:
        print("⚠️ Some tests failed. Logic may need adjustment.")
    
    print("=" * 50)


def simulate_extraction():
    """Simulate the full extraction process."""
    
    print("\n🔄 Simulating Full Extraction Process")
    print("=" * 50)
    
    # Mock implementation steps
    mock_steps = [
        {
            "step": 1,
            "title": "Create user registration endpoint",
            "description": "Implement the POST /api/auth/register endpoint to handle user registration.",
            "action": "Add a new route in the Express application.",
            "files": ["app/routes/auth.js"],
            "complexity": "medium"
        },
        {
            "step": 2,
            "title": "Implement input validation",
            "description": "Add validation logic for email format and password strength.",
            "action": "Use a validation library to enforce rules.",
            "files": ["app/middleware/validation.js"],
            "complexity": "medium"
        },
        {
            "step": 3,
            "title": "Hash password before storing",
            "description": "Implement password hashing using bcrypt before saving user data.",
            "action": "Integrate bcrypt hashing in the registration logic.",
            "files": ["app/controllers/authController.js"],
            "complexity": "low"
        },
        {
            "step": 4,
            "title": "Store user data in MongoDB",
            "description": "Save the user data in the MongoDB database with a created_at timestamp.",
            "action": "Create a user model and save user data.",
            "files": ["app/models/User.js"],
            "complexity": "medium"
        },
        {
            "step": 5,
            "title": "Generate JWT token",
            "description": "Return a JWT token upon successful registration.",
            "action": "Integrate JWT generation in the registration response.",
            "files": ["app/controllers/authController.js"],  # Duplicate - should be modify
            "complexity": "medium"
        },
        {
            "step": 6,
            "title": "Write unit tests for registration",
            "description": "Create comprehensive unit tests for the user registration functionality.",
            "action": "Add tests to ensure all scenarios are covered.",
            "files": ["tests/unit/auth.test.js"],
            "complexity": "medium"
        },
        {
            "step": 7,
            "title": "Update API documentation",
            "description": "Document the new /api/auth/register endpoint in the API documentation.",
            "action": "Add details about the endpoint, request body, and response.",
            "files": ["docs/api.md"],
            "complexity": "low"
        }
    ]
    
    files_to_create = []
    files_to_modify = []
    seen_files = set()
    
    print(f"🔍 Processing {len(mock_steps)} implementation steps...")
    
    for i, step in enumerate(mock_steps):
        step_files = step.get("files", [])
        step_title = step.get("title", f"Step {i+1}")
        
        print(f"\n  Step {i+1}: {step_title}")
        print(f"    Files: {step_files}")
        
        for file_path in step_files:
            # Check if we've seen this file before
            if file_path in seen_files:
                # File already processed - this should be a modification
                file_spec = {
                    "path": file_path,
                    "changes": step.get("description", step_title),
                    "complexity": step.get("complexity", "medium"),
                    "risk": "low"
                }
                files_to_modify.append(file_spec)
                print(f"    ✏️  MODIFY: {file_path} (already seen)")
            else:
                # New file - determine if create or modify
                if _is_new_file(file_path, step):
                    file_spec = {
                        "path": file_path,
                        "reason": step.get("description", step_title),
                        "template": f"Implement {step_title}",
                        "estimated_lines": 100,  # Simplified
                        "complexity": step.get("complexity", "medium")
                    }
                    files_to_create.append(file_spec)
                    print(f"    ✅ CREATE: {file_path}")
                else:
                    file_spec = {
                        "path": file_path,
                        "changes": step.get("description", step_title),
                        "complexity": step.get("complexity", "medium"),
                        "risk": "low"
                    }
                    files_to_modify.append(file_spec)
                    print(f"    ✏️  MODIFY: {file_path}")
                
                seen_files.add(file_path)
    
    print(f"\n🎯 FINAL RESULT:")
    print(f"  ✅ Files to CREATE: {len(files_to_create)}")
    for file_spec in files_to_create:
        print(f"    - {file_spec['path']}")
    
    print(f"  ✏️  Files to MODIFY: {len(files_to_modify)}")
    for file_spec in files_to_modify:
        print(f"    - {file_spec['path']}")
    
    total_operations = len(files_to_create) + len(files_to_modify)
    print(f"\n📊 TOTAL FILE OPERATIONS: {total_operations}")
    
    if total_operations > 0:
        print("✅ SUCCESS: File operations extracted successfully!")
        print("✅ This should fix the 'No file operations specified' error!")
    else:
        print("❌ FAILED: No file operations extracted")
    
    print("=" * 50)


if __name__ == "__main__":
    test_file_classification()
    simulate_extraction()
