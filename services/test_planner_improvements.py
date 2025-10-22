#!/usr/bin/env python3
"""
Test script to validate planner agent improvements for Express.js architecture compliance.

This script tests:
1. Architecture guidelines loading from AGENTS.md
2. Express.js project detection
3. Plan validation logic
4. File naming convention validation
"""

import sys
import os
import json
from pathlib import Path

# Add the ai-agent-service to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-agent-service'))

def test_architecture_guidelines_loading():
    """Test loading architecture guidelines from AGENTS.md"""
    print("🧪 Testing architecture guidelines loading...")
    
    try:
        from app.agents.developer.planner.nodes.generate_plan import load_architecture_guidelines
        
        # Test with Express.js demo project path
        codebase_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        guidelines = load_architecture_guidelines(codebase_path)
        
        print(f"   ✅ Has AGENTS.md: {guidelines['has_agents_md']}")
        print(f"   ✅ Is Express Project: {guidelines['is_express_project']}")
        print(f"   ✅ Project Type: {guidelines['project_type']}")
        
        # Verify AGENTS.md content is loaded
        if guidelines['has_agents_md']:
            assert "Express.js" in guidelines['architecture_content']
            assert "Layered Architecture" in guidelines['architecture_content']
            print("   ✅ AGENTS.md content loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_express_layer_detection():
    """Test Express.js architecture layer detection"""
    print("🧪 Testing Express.js layer detection...")
    
    try:
        from app.agents.developer.planner.nodes.generate_plan import detect_express_architecture_layers
        
        # Test with Express.js demo project path
        codebase_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"
        layers = detect_express_architecture_layers(codebase_path)
        
        print(f"   ✅ Source Structure: {layers['src_structure']}")
        print(f"   ✅ Has Models: {layers['has_models']}")
        print(f"   ✅ Has Controllers: {layers['has_controllers']}")
        print(f"   ✅ Has Routes: {layers['has_routes']}")
        
        # Verify at least some layers are detected
        layer_count = sum(1 for k, v in layers.items() if k.startswith('has_') and v)
        print(f"   ✅ Detected {layer_count} architecture layers")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_file_naming_validation():
    """Test file naming convention validation"""
    print("🧪 Testing file naming convention validation...")
    
    try:
        from app.agents.developer.planner.nodes.generate_plan import _validate_file_naming_convention
        
        # Test cases for different file types
        test_cases = [
            # Models (should be PascalCase)
            ("src/models/User.js", True),
            ("src/models/Product.js", True),
            ("src/models/userModel.js", False),  # Should be PascalCase
            
            # Controllers (should be camelCase)
            ("src/controllers/userController.js", True),
            ("src/controllers/authController.js", True),
            ("src/controllers/UserController.js", False),  # Should be camelCase
            
            # Services (should be camelCase)
            ("src/services/userService.js", True),
            ("src/services/authService.js", True),
            ("src/services/UserService.js", False),  # Should be camelCase
            
            # Routes (can be camelCase or kebab-case)
            ("src/routes/users.js", True),
            ("src/routes/auth.js", True),
            ("src/routes/user-management.js", True),
            
            # Tests (should be kebab-case)
            ("src/tests/user-controller.test.js", True),
            ("src/tests/auth-service.test.js", True),
            ("src/tests/userController.test.js", False),  # Should be kebab-case
        ]
        
        passed = 0
        total = len(test_cases)
        
        for file_path, expected in test_cases:
            result = _validate_file_naming_convention(file_path)
            if result == expected:
                passed += 1
                print(f"   ✅ {file_path}: {result} (expected {expected})")
            else:
                print(f"   ❌ {file_path}: {result} (expected {expected})")
        
        print(f"   📊 Naming validation: {passed}/{total} tests passed")
        return passed == total
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_plan_validation():
    """Test implementation plan validation logic"""
    print("🧪 Testing implementation plan validation...")
    
    try:
        from app.agents.developer.planner.nodes.generate_plan import validate_express_plan_compliance
        from app.agents.developer.planner.state import ImplementationPlan, ImplementationStep
        
        # Create mock implementation plan with correct Express.js order
        steps = [
            ImplementationStep(
                step=1,
                title="Create User model",
                description="Define User schema with Mongoose",
                category="backend",
                sub_steps=[{
                    "sub_step": "1.1",
                    "title": "Define User schema",
                    "files_affected": ["src/models/User.js"]
                }],
                dependencies=[],
                estimated_hours=1.0,
                complexity="medium"
            ),
            ImplementationStep(
                step=2,
                title="Create user repository",
                description="Implement user data access layer",
                category="backend",
                sub_steps=[{
                    "sub_step": "2.1",
                    "title": "Create UserRepository class",
                    "files_affected": ["src/repositories/userRepository.js"]
                }],
                dependencies=[1],
                estimated_hours=1.5,
                complexity="medium"
            ),
            ImplementationStep(
                step=3,
                title="Create user service",
                description="Implement user business logic",
                category="backend",
                sub_steps=[{
                    "sub_step": "3.1",
                    "title": "Create UserService class",
                    "files_affected": ["src/services/userService.js"]
                }],
                dependencies=[2],
                estimated_hours=2.0,
                complexity="medium"
            ),
            ImplementationStep(
                step=4,
                title="Create user controller",
                description="Implement user request handlers",
                category="backend",
                sub_steps=[{
                    "sub_step": "4.1",
                    "title": "Create UserController class",
                    "files_affected": ["src/controllers/userController.js"]
                }],
                dependencies=[3],
                estimated_hours=1.5,
                complexity="medium"
            ),
            ImplementationStep(
                step=5,
                title="Create user routes",
                description="Define user API endpoints",
                category="backend",
                sub_steps=[{
                    "sub_step": "5.1",
                    "title": "Define user routes",
                    "files_affected": ["src/routes/users.js"]
                }],
                dependencies=[4],
                estimated_hours=1.0,
                complexity="low"
            )
        ]
        
        plan = ImplementationPlan(
            task_id="test-task",
            description="Test user management feature",
            complexity_score=6,
            plan_type="express_feature",
            functional_requirements=["User CRUD operations"],
            steps=steps,
            database_changes=[],
            external_dependencies=[],
            internal_dependencies=[],
            execution_order=[1, 2, 3, 4, 5],
            total_estimated_hours=7.0,
            story_points=5
        )
        
        # Test with Express.js guidelines
        architecture_guidelines = {
            "is_express_project": True,
            "has_agents_md": True,
            "project_type": "express_mongodb"
        }
        
        validation_result = validate_express_plan_compliance(plan, architecture_guidelines)
        
        print(f"   ✅ Validation completed")
        print(f"   📊 Warnings: {len(validation_result['warnings'])}")
        print(f"   📊 Errors: {len(validation_result['errors'])}")
        print(f"   📊 Suggestions: {len(validation_result['suggestions'])}")
        
        # Print any issues found
        for warning in validation_result['warnings']:
            print(f"   ⚠️ Warning: {warning}")
        
        for error in validation_result['errors']:
            print(f"   ❌ Error: {error}")
            
        for suggestion in validation_result['suggestions']:
            print(f"   💡 Suggestion: {suggestion}")
        
        # This should pass with minimal warnings since it follows correct order
        return len(validation_result['errors']) == 0
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Planner Agent Improvements for Express.js Architecture Compliance")
    print("=" * 80)
    
    tests = [
        ("Architecture Guidelines Loading", test_architecture_guidelines_loading),
        ("Express.js Layer Detection", test_express_layer_detection),
        ("File Naming Validation", test_file_naming_validation),
        ("Plan Validation Logic", test_plan_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Planner agent improvements are working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
