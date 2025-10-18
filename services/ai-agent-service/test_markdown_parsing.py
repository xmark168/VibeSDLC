#!/usr/bin/env python3
"""
Test script để kiểm tra logic xử lý markdown code blocks
"""

import json


def clean_llm_output(llm_output: str) -> str:
    """Clean LLM output by removing markdown code blocks"""
    cleaned_output = llm_output.strip()
    if cleaned_output.startswith("```json"):
        cleaned_output = cleaned_output[7:]  # Remove ```json
    elif cleaned_output.startswith("```"):
        cleaned_output = cleaned_output[3:]  # Remove ```
    if cleaned_output.endswith("```"):
        cleaned_output = cleaned_output[:-3]  # Remove trailing ```
    cleaned_output = cleaned_output.strip()
    return cleaned_output


def test_markdown_parsing():
    """Test các trường hợp khác nhau của LLM response"""
    
    # Test case 1: JSON wrapped trong ```json
    test1 = '''```json
{
    "functional_requirements": [
        "User-facing functionality required",
        "API endpoint implementation required"
    ],
    "acceptance_criteria": [
        "User can successfully interact with the feature",
        "API endpoint returns expected response"
    ],
    "business_rules": {
        "auth": "User must be authenticated"
    },
    "technical_specs": {
        "api_type": "REST API",
        "database": "PostgreSQL"
    },
    "assumptions": ["Development environment is set up"],
    "constraints": ["Must follow existing patterns"]
}
```'''

    # Test case 2: JSON wrapped trong ```
    test2 = '''```
{
    "files_to_create": [
        {
            "path": "app/api/routes/users.py",
            "purpose": "User profile endpoints",
            "complexity": "medium",
            "estimated_lines": 150
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
            "purpose": "Get user profile",
            "status": "to_create"
        }
    ]
}
```'''

    # Test case 3: Plain JSON (không có markdown)
    test3 = '''{
    "complexity_score": 8,
    "plan_type": "complex",
    "approach": {
        "strategy": "Create new components following existing patterns",
        "pattern": "Follow existing patterns in codebase",
        "architecture_alignment": "Aligns with current service-oriented architecture"
    },
    "implementation_steps": [
        {
            "step": 1,
            "title": "Create user profile API",
            "description": "Implement user profile endpoints",
            "estimated_hours": 4.0,
            "complexity": "medium"
        }
    ],
    "estimated_hours": 12.5,
    "story_points": 8
}'''

    print("🧪 Testing markdown parsing logic...")
    print("=" * 60)
    
    # Test case 1
    print("\n📝 Test Case 1: JSON wrapped in ```json")
    print(f"Raw input: {test1[:50]}...")
    cleaned1 = clean_llm_output(test1)
    print(f"Cleaned: {cleaned1[:50]}...")
    try:
        parsed1 = json.loads(cleaned1)
        print(f"✅ SUCCESS: Parsed {len(parsed1.get('functional_requirements', []))} requirements")
        print(f"   - Requirements: {parsed1.get('functional_requirements', [])}")
        print(f"   - Criteria: {len(parsed1.get('acceptance_criteria', []))} items")
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: {e}")
    
    # Test case 2
    print("\n📝 Test Case 2: JSON wrapped in ```")
    print(f"Raw input: {test2[:50]}...")
    cleaned2 = clean_llm_output(test2)
    print(f"Cleaned: {cleaned2[:50]}...")
    try:
        parsed2 = json.loads(cleaned2)
        print(f"✅ SUCCESS: Parsed {len(parsed2.get('files_to_create', []))} files to create")
        print(f"   - Files to create: {len(parsed2.get('files_to_create', []))}")
        print(f"   - Files to modify: {len(parsed2.get('files_to_modify', []))}")
        print(f"   - API endpoints: {len(parsed2.get('api_endpoints', []))}")
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: {e}")
    
    # Test case 3
    print("\n📝 Test Case 3: Plain JSON (no markdown)")
    print(f"Raw input: {test3[:50]}...")
    cleaned3 = clean_llm_output(test3)
    print(f"Cleaned: {cleaned3[:50]}...")
    try:
        parsed3 = json.loads(cleaned3)
        print(f"✅ SUCCESS: Parsed complexity {parsed3.get('complexity_score')}/10")
        print(f"   - Plan type: {parsed3.get('plan_type')}")
        print(f"   - Steps: {len(parsed3.get('implementation_steps', []))}")
        print(f"   - Hours: {parsed3.get('estimated_hours')}")
        print(f"   - Story points: {parsed3.get('story_points')}")
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 All test cases completed!")


if __name__ == "__main__":
    test_markdown_parsing()
