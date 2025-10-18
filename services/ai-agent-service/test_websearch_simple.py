"""
Simple WebSearch Integration Test

Test đơn giản để kiểm tra websearch integration không cần pytest.
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_websearch_decision():
    """Test logic quyết định websearch."""
    try:
        from app.agents.developer.planner.tools.tavily_search import should_perform_websearch
        
        # Test case 1: Task với search indicators
        task_description = "Implement user authentication with best practices and security"
        task_requirements = {
            "requirements": ["Authentication", "Security", "Best practices"],
            "technical_specs": {"framework": "FastAPI"}
        }
        
        should_search, reason = should_perform_websearch(
            task_description=task_description,
            task_requirements=task_requirements,
            codebase_context="Basic FastAPI app"
        )
        
        print(f"✅ Test 1 - Should search: {should_search}")
        print(f"   Reason: {reason}")
        assert should_search is True, "Should search for task with best practices"
        
        # Test case 2: Task đơn giản
        task_description = "Fix typo in user model"
        task_requirements = {
            "requirements": ["Fix typo"],
            "technical_specs": {"file": "models/user.py", "line": "25"}
        }
        
        should_search, reason = should_perform_websearch(
            task_description=task_description,
            task_requirements=task_requirements,
            codebase_context="Well-documented FastAPI app with user models"
        )
        
        print(f"✅ Test 2 - Should search: {should_search}")
        print(f"   Reason: {reason}")
        assert should_search is False, "Should not search for simple task"
        
        print("✅ WebSearch decision logic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ WebSearch decision test failed: {e}")
        return False


def test_search_queries():
    """Test generation của search queries."""
    try:
        from app.agents.developer.planner.tools.tavily_search import generate_search_queries
        
        task_description = "Implement JWT authentication with refresh tokens"
        task_requirements = {
            "requirements": ["JWT auth", "Refresh tokens", "Security"],
            "technical_specs": {"framework": "FastAPI", "database": "PostgreSQL"}
        }
        
        queries = generate_search_queries(task_description, task_requirements)
        
        print(f"✅ Generated {len(queries)} search queries:")
        for i, query in enumerate(queries, 1):
            print(f"   {i}. {query}")
        
        assert len(queries) > 0, "Should generate at least one query"
        assert len(queries) <= 3, "Should limit to 3 queries"
        
        print("✅ Search queries generation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Search queries test failed: {e}")
        return False


def test_websearch_node():
    """Test websearch node với mock data."""
    try:
        from app.agents.developer.planner.state import PlannerState, TaskRequirements
        from app.agents.developer.planner.nodes.websearch import websearch
        
        # Test case: Skip websearch
        state = PlannerState(
            task_description="Fix simple bug in user model",
            codebase_context="Well-documented codebase",
            task_requirements=TaskRequirements(
                task_id="TSK-001",
                requirements=["Fix bug"],
                technical_specs={"file": "models/user.py"}
            )
        )
        
        # Mock should_perform_websearch để return False
        import app.agents.developer.planner.nodes.websearch as websearch_module
        original_should_search = websearch_module.should_perform_websearch
        
        def mock_should_search(*args, **kwargs):
            return False, "Simple task with sufficient context"
        
        websearch_module.should_perform_websearch = mock_should_search
        
        try:
            result_state = websearch(state)
            
            print(f"✅ WebSearch node test:")
            print(f"   Performed: {result_state.websearch_results.performed}")
            print(f"   Reason: {result_state.websearch_results.reason_for_skip}")
            print(f"   Next phase: {result_state.current_phase}")
            
            assert result_state.websearch_results.performed is False
            assert result_state.current_phase == "analyze_codebase"
            assert result_state.status == "websearch_completed"
            
            print("✅ WebSearch node tests passed!")
            return True
            
        finally:
            # Restore original function
            websearch_module.should_perform_websearch = original_should_search
        
    except Exception as e:
        print(f"❌ WebSearch node test failed: {e}")
        return False


def test_state_model():
    """Test WebSearchResults state model."""
    try:
        from app.agents.developer.planner.state import WebSearchResults, PlannerState
        
        # Test WebSearchResults model
        search_results = WebSearchResults(
            performed=True,
            queries=["test query 1", "test query 2"],
            results=[
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.9
                }
            ],
            summary="Test summary",
            search_time=1.5,
            reason_for_search="Need external information"
        )
        
        print(f"✅ WebSearchResults model test:")
        print(f"   Performed: {search_results.performed}")
        print(f"   Queries: {len(search_results.queries)}")
        print(f"   Results: {len(search_results.results)}")
        print(f"   Search time: {search_results.search_time}s")
        
        # Test PlannerState với websearch_results
        state = PlannerState(
            task_description="Test task",
            websearch_results=search_results
        )
        
        assert state.websearch_results.performed is True
        assert len(state.websearch_results.queries) == 2
        assert state.websearch_results.search_time == 1.5
        
        print("✅ State model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ State model test failed: {e}")
        return False


def main():
    """Chạy tất cả tests."""
    print("🧪 Running WebSearch Integration Tests")
    print("=" * 50)
    
    tests = [
        ("WebSearch Decision Logic", test_websearch_decision),
        ("Search Queries Generation", test_search_queries),
        ("WebSearch Node", test_websearch_node),
        ("State Model", test_state_model),
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
        print("🎉 All tests passed! WebSearch integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
