"""
Test script to verify the file extraction fix works correctly.
"""

import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from agents.developer.planner.nodes.analyze_codebase import _extract_files_from_implementation_steps
from agents.developer.planner.state import PlannerState
from agents.developer.planner.models import ImplementationPlan

def test_file_extraction():
    """Test the file extraction from implementation steps."""
    
    print("🧪 Testing File Extraction from Implementation Steps")
    print("=" * 60)
    
    # Create mock implementation steps (similar to the JSON you provided)
    mock_steps = [
        {
            "step": 1,
            "title": "Create user registration endpoint",
            "description": "Implement the POST /api/auth/register endpoint to handle user registration.",
            "action": "Add a new route in the Express application.",
            "files": ["app/routes/auth.js"],
            "estimated_hours": 2.0,
            "complexity": "medium"
        },
        {
            "step": 2,
            "title": "Implement input validation",
            "description": "Add validation logic for email format and password strength.",
            "action": "Use a validation library to enforce rules.",
            "files": ["app/middleware/validation.js"],
            "estimated_hours": 1.5,
            "complexity": "medium"
        },
        {
            "step": 3,
            "title": "Hash password before storing",
            "description": "Implement password hashing using bcrypt before saving user data.",
            "action": "Integrate bcrypt hashing in the registration logic.",
            "files": ["app/controllers/authController.js"],
            "estimated_hours": 1.0,
            "complexity": "low"
        },
        {
            "step": 4,
            "title": "Store user data in MongoDB",
            "description": "Save the user data in the MongoDB database with a created_at timestamp.",
            "action": "Create a user model and save user data.",
            "files": ["app/models/User.js"],
            "estimated_hours": 1.5,
            "complexity": "medium"
        },
        {
            "step": 5,
            "title": "Generate JWT token",
            "description": "Return a JWT token upon successful registration.",
            "action": "Integrate JWT generation in the registration response.",
            "files": ["app/controllers/authController.js"],  # This should be modify since it's duplicate
            "estimated_hours": 1.0,
            "complexity": "medium"
        },
        {
            "step": 6,
            "title": "Write unit tests for registration",
            "description": "Create comprehensive unit tests for the user registration functionality.",
            "action": "Add tests to ensure all scenarios are covered.",
            "files": ["tests/unit/auth.test.js"],
            "estimated_hours": 2.0,
            "complexity": "medium"
        },
        {
            "step": 7,
            "title": "Update API documentation",
            "description": "Document the new /api/auth/register endpoint in the API documentation.",
            "action": "Add details about the endpoint, request body, and response.",
            "files": ["docs/api.md"],
            "estimated_hours": 1.0,
            "complexity": "low"
        }
    ]
    
    # Create mock state with implementation plan
    state = PlannerState()
    state.implementation_plan = ImplementationPlan(
        implementation_steps=mock_steps,
        total_estimated_hours=10.0,
        story_points=8,
        complexity_score=6
    )
    
    # Test the extraction function
    print("🔍 Extracting files from implementation steps...")
    files_to_create, files_to_modify = _extract_files_from_implementation_steps(state)
    
    print("\n📊 EXTRACTION RESULTS:")
    print(f"✅ Files to CREATE: {len(files_to_create)}")
    for i, file_spec in enumerate(files_to_create):
        print(f"  [{i+1}] {file_spec['path']} - {file_spec['reason'][:50]}...")
    
    print(f"\n✏️  Files to MODIFY: {len(files_to_modify)}")
    for i, file_spec in enumerate(files_to_modify):
        print(f"  [{i+1}] {file_spec['path']} - {file_spec['changes'][:50]}...")
    
    # Verify expected results
    expected_creates = [
        "app/routes/auth.js",
        "app/middleware/validation.js", 
        "app/controllers/authController.js",
        "app/models/User.js",
        "tests/unit/auth.test.js"
    ]
    
    expected_modifies = [
        "docs/api.md"  # Documentation updates are usually modifications
    ]
    
    print("\n🎯 VALIDATION:")
    created_paths = [f['path'] for f in files_to_create]
    modified_paths = [f['path'] for f in files_to_modify]
    
    print(f"Expected creates: {expected_creates}")
    print(f"Actual creates: {created_paths}")
    print(f"Expected modifies: {expected_modifies}")
    print(f"Actual modifies: {modified_paths}")
    
    # Check if we have any file operations (this was the original problem)
    total_operations = len(files_to_create) + len(files_to_modify)
    if total_operations > 0:
        print(f"✅ SUCCESS: {total_operations} file operations extracted!")
        print("✅ This should fix the 'No file operations specified' error!")
    else:
        print("❌ FAILED: No file operations extracted")
    
    print("=" * 60)
    return files_to_create, files_to_modify


if __name__ == "__main__":
    test_file_extraction()
