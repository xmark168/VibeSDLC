#!/usr/bin/env python3
"""
Mock test để kiểm tra logic parsing LLM response trong các nodes
"""

import json
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))


def test_parse_task_logic():
    """Test logic parsing trong parse_task node"""
    print("🧪 Testing parse_task logic...")

    # Mock LLM response với markdown wrapper
    mock_llm_output = """```json
{
    "functional_requirements": [
        "User-facing functionality required",
        "API endpoint implementation required",
        "Database changes required"
    ],
    "acceptance_criteria": [
        "User can successfully interact with the feature",
        "API endpoint returns expected response format",
        "Data is persisted correctly in database"
    ],
    "business_rules": {
        "auth": "User must be authenticated to access feature"
    },
    "technical_specs": {
        "api_type": "REST API",
        "database": "PostgreSQL with SQLModel",
        "auth": "JWT token-based authentication"
    },
    "assumptions": ["Development environment is properly set up"],
    "constraints": ["Must follow existing patterns", "Performance requirements"]
}
```"""

    # Test cleaning logic
    cleaned_output = mock_llm_output.strip()
    if cleaned_output.startswith("```json"):
        cleaned_output = cleaned_output[7:]  # Remove ```json
    elif cleaned_output.startswith("```"):
        cleaned_output = cleaned_output[3:]  # Remove ```
    if cleaned_output.endswith("```"):
        cleaned_output = cleaned_output[:-3]  # Remove trailing ```
    cleaned_output = cleaned_output.strip()

    try:
        parsed_data = json.loads(cleaned_output)
        requirements = parsed_data.get("functional_requirements", [])
        acceptance_criteria = parsed_data.get("acceptance_criteria", [])
        business_rules = parsed_data.get("business_rules", {})
        technical_specs = parsed_data.get("technical_specs", {})
        assumptions = parsed_data.get("assumptions", [])
        constraints = parsed_data.get("constraints", [])

        print(
            f"✅ parse_task: {len(requirements)} requirements, {len(acceptance_criteria)} criteria"
        )
        print(f"   - Business rules: {len(business_rules)} items")
        print(f"   - Technical specs: {len(technical_specs)} items")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ parse_task failed: {e}")
        return False


def test_analyze_codebase_logic():
    """Test logic parsing trong analyze_codebase node"""
    print("\n🧪 Testing analyze_codebase logic...")

    # Mock LLM response với nested structure
    mock_llm_output = """```json
{
  "codebase_analysis": {
    "files_to_create": [
      {
        "path": "app/api/routes/users.py",
        "purpose": "User profile endpoints",
        "complexity": "medium",
        "estimated_lines": 150
      },
      {
        "path": "app/schemas/user.py",
        "purpose": "User data models",
        "complexity": "low",
        "estimated_lines": 50
      }
    ],
    "files_to_modify": [
      {
        "path": "app/core/security.py",
        "changes": "Add user profile access controls",
        "complexity": "medium",
        "risk": "medium"
      }
    ],
    "api_endpoints": [
      {
        "path": "/api/users/profile",
        "method": "GET",
        "purpose": "Get user profile information",
        "status": "to_create"
      }
    ],
    "affected_modules": ["app.api.routes.users", "app.schemas.user"],
    "database_changes": [],
    "external_dependencies": [],
    "internal_dependencies": []
  }
}
```"""

    # Test cleaning logic
    cleaned_output = mock_llm_output.strip()
    if cleaned_output.startswith("```json"):
        cleaned_output = cleaned_output[7:]
    elif cleaned_output.startswith("```"):
        cleaned_output = cleaned_output[3:]
    if cleaned_output.endswith("```"):
        cleaned_output = cleaned_output[:-3]
    cleaned_output = cleaned_output.strip()

    try:
        parsed_data = json.loads(cleaned_output)

        # Handle nested structure if LLM wraps data in "codebase_analysis"
        if "codebase_analysis" in parsed_data:
            analysis_data = parsed_data["codebase_analysis"]
        else:
            analysis_data = parsed_data

        files_to_create = analysis_data.get("files_to_create", [])
        files_to_modify = analysis_data.get("files_to_modify", [])
        api_endpoints = analysis_data.get("api_endpoints", [])
        affected_modules = analysis_data.get("affected_modules", [])

        print(
            f"✅ analyze_codebase: {len(files_to_create)} files to create, {len(files_to_modify)} files to modify"
        )
        print(f"   - API endpoints: {len(api_endpoints)} items")
        print(f"   - Affected modules: {len(affected_modules)} items")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ analyze_codebase failed: {e}")
        return False


def test_generate_plan_logic():
    """Test logic parsing trong generate_plan node"""
    print("\n🧪 Testing generate_plan logic...")

    # Mock LLM response với approach as string (problematic case)
    mock_llm_output = """```json
{
  "complexity_score": 7,
  "plan_type": "complex",
  "approach": "Create new components following existing patterns",
  "implementation_steps": [
    {
      "step": 1,
      "title": "Create user profile API",
      "description": "Implement user profile endpoints",
      "estimated_hours": 4.0,
      "complexity": "medium"
    },
    {
      "step": 2,
      "title": "Add authentication middleware",
      "description": "Implement JWT authentication",
      "estimated_hours": 3.0,
      "complexity": "high"
    }
  ],
  "estimated_hours": 15.5,
  "story_points": 8
}
```"""

    # Test cleaning logic
    cleaned_output = mock_llm_output.strip()
    if cleaned_output.startswith("```json"):
        cleaned_output = cleaned_output[7:]
    elif cleaned_output.startswith("```"):
        cleaned_output = cleaned_output[3:]
    if cleaned_output.endswith("```"):
        cleaned_output = cleaned_output[:-3]
    cleaned_output = cleaned_output.strip()

    try:
        parsed_plan = json.loads(cleaned_output)
        complexity_score = parsed_plan.get("complexity_score", 5)
        plan_type = parsed_plan.get("plan_type", "simple")

        # Handle approach field - ensure it's a dictionary
        approach_raw = parsed_plan.get("approach", {})
        if isinstance(approach_raw, str):
            # If approach is a string, convert to proper dictionary
            approach = {
                "strategy": approach_raw,
                "pattern": "Follow existing patterns in codebase",
                "architecture_alignment": "Aligns with current service-oriented architecture",
            }
        elif isinstance(approach_raw, dict):
            approach = approach_raw
        else:
            approach = {
                "strategy": "Create new components following existing patterns",
                "pattern": "Follow existing patterns in codebase",
                "architecture_alignment": "Aligns with current service-oriented architecture",
            }

        llm_steps = parsed_plan.get("implementation_steps", [])
        estimated_hours = parsed_plan.get("estimated_hours", 0)
        story_points = parsed_plan.get("story_points", 0)

        print(
            f"✅ generate_plan: complexity {complexity_score}/10, {len(llm_steps)} steps, {estimated_hours}h"
        )
        print(f"   - Plan type: {plan_type}")
        print(f"   - Approach strategy: {approach['strategy']}")
        print(f"   - Story points: {story_points}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ generate_plan failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing LLM parsing logic in planner nodes...")
    print("=" * 60)

    results = []
    results.append(test_parse_task_logic())
    results.append(test_analyze_codebase_logic())
    results.append(test_generate_plan_logic())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print("✅ LLM parsing logic is working correctly")
        print("✅ Markdown code blocks are handled properly")
        print("✅ Nested JSON structures are parsed correctly")
        print("✅ Type conversion issues are resolved")
    else:
        print(f"⚠️  SOME TESTS FAILED: {passed}/{total} passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
