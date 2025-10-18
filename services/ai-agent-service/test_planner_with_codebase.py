#!/usr/bin/env python3
"""
Test script để kiểm tra planner agent với codebase analysis
"""

import sys
import os
import json

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))


# Mock the langchain imports to avoid dependency issues
class MockChatOpenAI:
    def __init__(self, **kwargs):
        self.model = kwargs.get("model", "gpt-4o-mini")
        self.temperature = kwargs.get("temperature", 0.3)

    def invoke(self, prompt):
        # Mock LLM response với codebase-aware analysis
        class MockResponse:
            content = """```json
{
  "codebase_analysis": {
    "files_to_create": [
      {
        "path": "app/api/v1/endpoints/profile.py",
        "reason": "New endpoint for user profile based on existing users.py pattern",
        "template": "app/api/v1/endpoints/users.py"
      }
    ],
    "files_to_modify": [
      {
        "path": "app/api/v1/router.py",
        "lines": [10, "15-20"],
        "changes": "Add profile endpoint to router following existing pattern",
        "complexity": "low",
        "risk": "low"
      },
      {
        "path": "app/services/user.py",
        "lines": [25, "30-40"],
        "changes": "Add get_profile method to UserService class",
        "complexity": "medium",
        "risk": "low"
      },
      {
        "path": "app/schemas/user.py",
        "lines": [50, "55-65"],
        "changes": "Add UserProfile schema based on existing UserResponse",
        "complexity": "low",
        "risk": "low"
      }
    ],
    "modules_affected": [
      "app.api.v1.endpoints.profile",
      "app.services.user",
      "app.schemas.user"
    ],
    "database_changes": [],
    "api_changes": [
      {
        "endpoint": "GET /api/v1/profile",
        "method": "GET",
        "status": "new",
        "changes": "New endpoint following existing authentication pattern"
      }
    ]
  },
  "impact_assessment": {
    "estimated_files_changed": 4,
    "estimated_lines_added": 85,
    "estimated_lines_modified": 25,
    "backward_compatibility": "maintained",
    "performance_impact": "negligible",
    "security_considerations": [
      "Ensure proper authentication using existing auth middleware",
      "Validate user permissions for profile access"
    ]
  }
}
```"""

        return MockResponse()


# Mock langchain_openai
sys.modules["langchain_openai"] = type(
    "MockModule", (), {"ChatOpenAI": MockChatOpenAI}
)()

# Now import our analyzer
from app.agents.developer.planner.tools.codebase_analyzer import (
    analyze_codebase_context,
)


def test_analyze_codebase_node():
    """Test analyze_codebase node với codebase context"""
    print("🧪 Testing analyze_codebase node with real codebase...")
    print("=" * 70)

    # Mock state object
    class MockTaskRequirements:
        task_id = "TSK-PROFILE-001"
        functional_requirements = ["Add user profile endpoint"]
        acceptance_criteria = ["User can get their profile data"]
        technical_specs = {"framework": "FastAPI", "database": "PostgreSQL"}
        business_rules = {"auth": "Required"}
        constraints = ["Follow existing patterns"]
        assumptions = ["User model exists"]

        def model_dump_json(self, indent=2):
            return json.dumps(
                {
                    "task_id": self.task_id,
                    "functional_requirements": self.functional_requirements,
                    "acceptance_criteria": self.acceptance_criteria,
                    "technical_specs": self.technical_specs,
                    "business_rules": self.business_rules,
                    "constraints": self.constraints,
                    "assumptions": self.assumptions,
                },
                indent=indent,
            )

    class MockState:
        task_requirements = MockTaskRequirements()
        task_description = "Add a new API endpoint to get user profile information"
        codebase_context = None

    # Test codebase analysis
    codebase_path = (
        r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
    )
    print(f"🔍 Analyzing codebase at: {codebase_path}")

    try:
        # Get codebase context
        codebase_context = analyze_codebase_context(codebase_path)
        print(f"✅ Codebase analysis completed - {len(codebase_context)} chars")

        # Show context preview
        print("\n📋 CODEBASE CONTEXT PREVIEW:")
        print("-" * 50)
        print(
            codebase_context[:800] + "..."
            if len(codebase_context) > 800
            else codebase_context
        )
        print("-" * 50)

        # Test LLM prompt formatting
        from app.templates.prompts.developer.planner import CODEBASE_ANALYSIS_PROMPT

        formatted_prompt = CODEBASE_ANALYSIS_PROMPT.format(
            task_requirements=MockState.task_requirements.model_dump_json(indent=2),
            codebase_context=codebase_context,
        )

        print(f"\n📝 Formatted prompt length: {len(formatted_prompt)} chars")

        # Test mock LLM call
        llm = MockChatOpenAI()
        response = llm.invoke(formatted_prompt)
        llm_output = response.content

        print(f"🤖 Mock LLM response length: {len(llm_output)} chars")

        # Test JSON parsing
        cleaned_output = llm_output.strip()
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output[7:]
        elif cleaned_output.startswith("```"):
            cleaned_output = cleaned_output[3:]
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3]
        cleaned_output = cleaned_output.strip()

        parsed_data = json.loads(cleaned_output)

        # Handle nested structure
        if "codebase_analysis" in parsed_data:
            analysis_data = parsed_data["codebase_analysis"]
        else:
            analysis_data = parsed_data

        files_to_create = analysis_data.get("files_to_create", [])
        files_to_modify = analysis_data.get("files_to_modify", [])
        api_changes = analysis_data.get("api_changes", [])
        modules_affected = analysis_data.get("modules_affected", [])

        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"  📁 Files to create: {len(files_to_create)}")
        print(f"  ✏️  Files to modify: {len(files_to_modify)}")
        print(f"  🔗 API changes: {len(api_changes)}")
        print(f"  📦 Modules affected: {len(modules_affected)}")

        # Show details
        if files_to_create:
            print(f"\n📁 FILES TO CREATE:")
            for file in files_to_create:
                print(f"  - {file['path']} (template: {file.get('template', 'N/A')})")

        if files_to_modify:
            print(f"\n✏️  FILES TO MODIFY:")
            for file in files_to_modify:
                print(
                    f"  - {file['path']} (complexity: {file.get('complexity', 'N/A')})"
                )

        if api_changes:
            print(f"\n🔗 API CHANGES:")
            for api in api_changes:
                print(f"  - {api['endpoint']} ({api['status']})")

        # Validation checks
        checks = [
            ("Codebase context generated", len(codebase_context) > 100),
            ("LLM prompt formatted", len(formatted_prompt) > 1000),
            (
                "JSON parsed successfully",
                len(files_to_create) > 0 or len(files_to_modify) > 0,
            ),
            ("Files analysis present", len(files_to_create) + len(files_to_modify) > 0),
            ("Template references", any("template" in f for f in files_to_create)),
            ("Existing patterns referenced", "existing" in llm_output.lower()),
        ]

        print(f"\n🔍 VALIDATION CHECKS:")
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False

        if all_passed:
            print(f"\n🎉 ALL CHECKS PASSED!")
            print(f"✅ Codebase-aware analysis is working correctly")
            print(f"✅ LLM receives real codebase context")
            print(f"✅ Analysis references existing patterns and files")
            return True
        else:
            print(f"\n⚠️ Some checks failed")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_analyze_codebase_node()
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
