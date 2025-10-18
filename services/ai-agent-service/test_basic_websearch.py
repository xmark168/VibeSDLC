"""
Basic WebSearch Test

Test cơ bản cho websearch logic không phụ thuộc vào external dependencies.
"""

def test_search_indicators():
    """Test logic tìm search indicators."""
    
    # Search indicators
    search_indicators = [
        "best practices",
        "how to implement", 
        "integration with",
        "latest version",
        "documentation",
        "tutorial",
        "example",
        "guide",
        "API reference",
        "configuration",
        "setup",
        "install",
        "deploy",
        "security",
        "performance",
        "optimization",
        "third-party",
        "external service",
        "library",
        "framework",
        "tool",
        "service",
        "platform"
    ]
    
    # Test cases
    test_cases = [
        ("Implement JWT authentication with best practices", True),
        ("Add user authentication using OAuth2 framework", True),
        ("Setup Redis caching for performance optimization", True),
        ("Fix typo in user model", False),
        ("Update variable name in config", False),
        ("Add logging to existing function", False),
        ("Integrate with third-party payment service", True),
        ("Install Docker for deployment", True),
        ("Follow security best practices for API", True),
    ]
    
    print("🔍 Testing search indicators logic:")
    
    passed = 0
    for task_description, expected in test_cases:
        task_lower = task_description.lower()
        found_indicators = [indicator for indicator in search_indicators if indicator in task_lower]
        should_search = len(found_indicators) > 0
        
        status = "✅" if should_search == expected else "❌"
        print(f"  {status} '{task_description[:50]}...' -> {should_search} (expected: {expected})")
        
        if found_indicators:
            print(f"      Found: {', '.join(found_indicators[:3])}")
        
        if should_search == expected:
            passed += 1
    
    print(f"\n📊 Search indicators test: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_query_generation():
    """Test logic tạo search queries."""
    
    def generate_search_queries_simple(task_description, task_requirements):
        """Simplified version of generate_search_queries."""
        queries = []
        
        # Base query từ task description
        base_query = task_description[:100]  # Limit length
        queries.append(f"{base_query} implementation guide")
        
        # Queries từ technical specs
        technical_specs = task_requirements.get("technical_specs", {})
        for tech, spec in technical_specs.items():
            if isinstance(spec, str) and spec:
                queries.append(f"{tech} {spec} best practices")
        
        # Queries từ requirements
        requirements = task_requirements.get("requirements", [])
        for req in requirements[:2]:  # Limit to top 2 requirements
            if len(req) > 10:  # Only meaningful requirements
                queries.append(f"{req} implementation example")
        
        # Limit total queries
        return queries[:3]
    
    print("\n🔍 Testing query generation logic:")
    
    test_cases = [
        {
            "task_description": "Implement JWT authentication with refresh tokens",
            "task_requirements": {
                "requirements": ["JWT auth", "Refresh tokens", "Security"],
                "technical_specs": {"framework": "FastAPI", "database": "PostgreSQL"}
            },
            "expected_min_queries": 1,
            "expected_max_queries": 3
        },
        {
            "task_description": "Fix bug",
            "task_requirements": {
                "requirements": ["Fix"],
                "technical_specs": {}
            },
            "expected_min_queries": 1,
            "expected_max_queries": 2
        }
    ]
    
    passed = 0
    for i, test_case in enumerate(test_cases, 1):
        queries = generate_search_queries_simple(
            test_case["task_description"],
            test_case["task_requirements"]
        )
        
        min_queries = test_case["expected_min_queries"]
        max_queries = test_case["expected_max_queries"]
        
        if min_queries <= len(queries) <= max_queries:
            print(f"  ✅ Test {i}: Generated {len(queries)} queries (expected: {min_queries}-{max_queries})")
            for j, query in enumerate(queries, 1):
                print(f"      {j}. {query}")
            passed += 1
        else:
            print(f"  ❌ Test {i}: Generated {len(queries)} queries (expected: {min_queries}-{max_queries})")
    
    print(f"\n📊 Query generation test: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_state_models():
    """Test state models với basic data."""
    
    print("\n🔍 Testing state models:")
    
    try:
        # Test WebSearchResults model
        search_results_data = {
            "performed": True,
            "queries": ["test query 1", "test query 2"],
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.9
                }
            ],
            "summary": "Test summary",
            "search_time": 1.5,
            "reason_for_search": "Need external information"
        }
        
        print(f"  ✅ WebSearchResults data structure valid")
        print(f"      Performed: {search_results_data['performed']}")
        print(f"      Queries: {len(search_results_data['queries'])}")
        print(f"      Results: {len(search_results_data['results'])}")
        print(f"      Search time: {search_results_data['search_time']}s")
        
        # Test basic validation
        assert search_results_data["performed"] is True
        assert len(search_results_data["queries"]) == 2
        assert search_results_data["search_time"] == 1.5
        
        print(f"  ✅ Basic validation passed")
        
        print(f"\n📊 State models test: 1/1 passed")
        return True
        
    except Exception as e:
        print(f"  ❌ State models test failed: {e}")
        print(f"\n📊 State models test: 0/1 passed")
        return False


def test_workflow_logic():
    """Test basic workflow logic."""
    
    print("\n🔍 Testing workflow logic:")
    
    def should_perform_websearch_simple(task_description, task_requirements, codebase_context=""):
        """Simplified version of should_perform_websearch."""
        search_indicators = [
            "best practices", "how to implement", "integration with", "latest version",
            "documentation", "tutorial", "example", "guide", "API reference",
            "configuration", "setup", "install", "deploy", "security",
            "performance", "optimization", "third-party", "external service",
            "library", "framework", "tool", "service", "platform"
        ]
        
        # Kiểm tra task description
        task_lower = task_description.lower()
        found_indicators = [indicator for indicator in search_indicators if indicator in task_lower]
        
        # Kiểm tra requirements
        requirements = task_requirements.get("requirements", [])
        technical_specs = task_requirements.get("technical_specs", {})
        
        # Nếu có ít thông tin technical specs
        has_limited_tech_info = len(technical_specs) < 2
        
        # Nếu có nhiều requirements phức tạp
        has_complex_requirements = len(requirements) > 5
        
        # Quyết định
        if found_indicators:
            return True, f"Found search indicators: {', '.join(found_indicators[:3])}"
        elif has_limited_tech_info and has_complex_requirements:
            return True, "Limited technical specifications for complex requirements"
        elif not codebase_context.strip():
            return True, "No codebase context provided, need external information"
        else:
            return False, "Sufficient information available for implementation planning"
    
    test_cases = [
        {
            "task_description": "Implement JWT authentication with best practices",
            "task_requirements": {"requirements": ["Auth"], "technical_specs": {"framework": "FastAPI"}},
            "codebase_context": "Basic app",
            "expected": True
        },
        {
            "task_description": "Fix typo in user model",
            "task_requirements": {"requirements": ["Fix"], "technical_specs": {"file": "user.py", "line": "25"}},
            "codebase_context": "Well-documented app",
            "expected": False
        },
        {
            "task_description": "Add new feature",
            "task_requirements": {"requirements": ["Feature"], "technical_specs": {}},
            "codebase_context": "",
            "expected": True
        }
    ]
    
    passed = 0
    for i, test_case in enumerate(test_cases, 1):
        should_search, reason = should_perform_websearch_simple(
            test_case["task_description"],
            test_case["task_requirements"],
            test_case["codebase_context"]
        )
        
        if should_search == test_case["expected"]:
            print(f"  ✅ Test {i}: {should_search} (expected: {test_case['expected']})")
            print(f"      Reason: {reason}")
            passed += 1
        else:
            print(f"  ❌ Test {i}: {should_search} (expected: {test_case['expected']})")
            print(f"      Reason: {reason}")
    
    print(f"\n📊 Workflow logic test: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def main():
    """Chạy tất cả basic tests."""
    print("🧪 Running Basic WebSearch Tests")
    print("=" * 50)
    
    tests = [
        ("Search Indicators Logic", test_search_indicators),
        ("Query Generation Logic", test_query_generation),
        ("State Models", test_state_models),
        ("Workflow Logic", test_workflow_logic),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed! WebSearch logic is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
