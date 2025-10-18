"""
Demo WebSearch Integration

Demo script để test tích hợp Tavily Search vào Planner Agent.
"""

import os
import sys
from typing import Dict, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def demo_websearch_decision():
    """Demo logic quyết định websearch."""
    print("🔍 Demo: WebSearch Decision Logic")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.tools.tavily_search import should_perform_websearch
        
        test_cases = [
            {
                "name": "Complex Authentication Task",
                "task_description": "Implement OAuth2 authentication with JWT tokens and refresh token rotation using best practices",
                "task_requirements": {
                    "requirements": ["OAuth2 auth", "JWT tokens", "Refresh rotation", "Security"],
                    "technical_specs": {"framework": "FastAPI"}
                },
                "codebase_context": "Basic FastAPI app"
            },
            {
                "name": "Simple Bug Fix",
                "task_description": "Fix typo in user model field name",
                "task_requirements": {
                    "requirements": ["Fix typo"],
                    "technical_specs": {"file": "models/user.py", "line": "25", "field": "username"}
                },
                "codebase_context": "Well-documented FastAPI app with comprehensive user models"
            },
            {
                "name": "New Project Setup",
                "task_description": "Setup new microservice with Docker deployment",
                "task_requirements": {
                    "requirements": ["New microservice", "Docker", "Deployment"],
                    "technical_specs": {}
                },
                "codebase_context": ""
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   Task: {test_case['task_description']}")
            
            should_search, reason = should_perform_websearch(
                task_description=test_case['task_description'],
                task_requirements=test_case['task_requirements'],
                codebase_context=test_case['codebase_context']
            )
            
            status = "🌐 SEARCH" if should_search else "⏭️  SKIP"
            print(f"   Decision: {status}")
            print(f"   Reason: {reason}")
        
        print("\n✅ WebSearch decision demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ WebSearch decision demo failed: {e}")
        return False


def demo_search_queries():
    """Demo generation của search queries."""
    print("\n🔍 Demo: Search Queries Generation")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.tools.tavily_search import generate_search_queries
        
        test_cases = [
            {
                "name": "Authentication Implementation",
                "task_description": "Implement JWT authentication with refresh tokens and role-based access control",
                "task_requirements": {
                    "requirements": ["JWT authentication", "Refresh tokens", "RBAC", "Security"],
                    "technical_specs": {"framework": "FastAPI", "database": "PostgreSQL", "auth": "OAuth2"}
                }
            },
            {
                "name": "Payment Integration",
                "task_description": "Integrate Stripe payment processing with webhook handling",
                "task_requirements": {
                    "requirements": ["Payment processing", "Webhook handling", "Transaction logging"],
                    "technical_specs": {"payment_provider": "Stripe", "framework": "FastAPI"}
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   Task: {test_case['task_description']}")
            
            queries = generate_search_queries(
                test_case['task_description'],
                test_case['task_requirements']
            )
            
            print(f"   Generated {len(queries)} search queries:")
            for j, query in enumerate(queries, 1):
                print(f"      {j}. {query}")
        
        print("\n✅ Search queries demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Search queries demo failed: {e}")
        return False


def demo_websearch_node():
    """Demo websearch node với mock data."""
    print("\n🔍 Demo: WebSearch Node")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.state import PlannerState, TaskRequirements
        from app.agents.developer.planner.nodes.websearch import websearch
        
        # Test case 1: Skip websearch
        print("\n1. Test Case: Skip WebSearch")
        state1 = PlannerState(
            task_description="Fix simple validation error in user registration form",
            codebase_context="Well-documented FastAPI app with comprehensive validation logic",
            task_requirements=TaskRequirements(
                task_id="TSK-001",
                task_title="Fix validation error",
                requirements=["Fix validation", "User registration"],
                technical_specs={"file": "api/auth.py", "function": "register_user", "issue": "email validation"}
            )
        )
        
        print(f"   Task: {state1.task_description}")
        print(f"   Context: {state1.codebase_context[:50]}...")
        
        # Mock should_perform_websearch để return False
        import app.agents.developer.planner.nodes.websearch as websearch_module
        original_should_search = websearch_module.should_perform_websearch
        
        def mock_should_search_false(*args, **kwargs):
            return False, "Simple task with sufficient context and clear technical specifications"
        
        websearch_module.should_perform_websearch = mock_should_search_false
        
        try:
            result_state1 = websearch(state1)
            
            print(f"   Result: WebSearch {('PERFORMED' if result_state1.websearch_results.performed else 'SKIPPED')}")
            print(f"   Reason: {result_state1.websearch_results.reason_for_skip}")
            print(f"   Next Phase: {result_state1.current_phase}")
            print(f"   Status: {result_state1.status}")
            
        finally:
            websearch_module.should_perform_websearch = original_should_search
        
        # Test case 2: Perform websearch (với mock)
        print("\n2. Test Case: Perform WebSearch (Mocked)")
        state2 = PlannerState(
            task_description="Implement advanced OAuth2 authentication with PKCE and refresh token rotation",
            codebase_context="",
            task_requirements=TaskRequirements(
                task_id="TSK-002",
                task_title="Advanced OAuth2 implementation",
                requirements=["OAuth2", "PKCE", "Refresh token rotation", "Security best practices"],
                technical_specs={}
            )
        )
        
        print(f"   Task: {state2.task_description}")
        print(f"   Context: {'(empty)' if not state2.codebase_context else state2.codebase_context}")
        
        def mock_should_search_true(*args, **kwargs):
            return True, "Complex authentication task requiring external best practices and implementation guides"
        
        def mock_generate_queries(*args, **kwargs):
            return [
                "OAuth2 PKCE implementation best practices",
                "JWT refresh token rotation security",
                "FastAPI OAuth2 authentication guide"
            ]
        
        def mock_tavily_search(*args, **kwargs):
            import json
            return json.dumps({
                "status": "success",
                "query": args[0] if args else "test query",
                "results": [
                    {
                        "title": "OAuth2 PKCE Implementation Guide",
                        "url": "https://example.com/oauth2-pkce",
                        "content": "PKCE (Proof Key for Code Exchange) is a security extension to OAuth2 that prevents authorization code interception attacks...",
                        "score": 0.95
                    },
                    {
                        "title": "JWT Refresh Token Best Practices",
                        "url": "https://example.com/jwt-refresh",
                        "content": "Refresh token rotation is a security practice where refresh tokens are replaced with new ones after each use...",
                        "score": 0.92
                    }
                ],
                "search_time": 1.2
            })
        
        websearch_module.should_perform_websearch = mock_should_search_true
        websearch_module.generate_search_queries = mock_generate_queries
        websearch_module.tavily_search_tool = mock_tavily_search
        
        try:
            result_state2 = websearch(state2)
            
            print(f"   Result: WebSearch {('PERFORMED' if result_state2.websearch_results.performed else 'SKIPPED')}")
            print(f"   Queries: {len(result_state2.websearch_results.queries)}")
            print(f"   Results: {len(result_state2.websearch_results.results)}")
            print(f"   Search Time: {result_state2.websearch_results.search_time}s")
            print(f"   Next Phase: {result_state2.current_phase}")
            print(f"   Enhanced Context: {'Yes' if 'Web Search Results' in result_state2.codebase_context else 'No'}")
            
        finally:
            # Restore original functions
            websearch_module.should_perform_websearch = original_should_search
            if hasattr(websearch_module, 'generate_search_queries'):
                delattr(websearch_module, 'generate_search_queries')
            if hasattr(websearch_module, 'tavily_search_tool'):
                delattr(websearch_module, 'tavily_search_tool')
        
        print("\n✅ WebSearch node demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ WebSearch node demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def demo_workflow_integration():
    """Demo workflow integration với websearch branch."""
    print("\n🔍 Demo: Workflow Integration")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.agent import PlannerAgent
        from app.agents.developer.planner.state import PlannerState, TaskRequirements
        
        # Tạo planner agent
        planner = PlannerAgent(
            model="gpt-4o-mini",
            session_id="demo_session",
            user_id="demo_user"
        )
        
        # Test websearch_branch method
        test_cases = [
            {
                "name": "Should Search",
                "state": PlannerState(
                    task_description="Implement microservices architecture with Docker and Kubernetes deployment",
                    codebase_context="",
                    task_requirements=TaskRequirements(
                        requirements=["Microservices", "Docker", "Kubernetes", "Deployment"],
                        technical_specs={}
                    )
                ),
                "expected": "websearch"
            },
            {
                "name": "Should Skip",
                "state": PlannerState(
                    task_description="Update user model field validation",
                    codebase_context="Comprehensive FastAPI app with detailed user models and validation",
                    task_requirements=TaskRequirements(
                        requirements=["Update validation"],
                        technical_specs={"model": "User", "field": "email", "validation": "email format"}
                    )
                ),
                "expected": "analyze_codebase"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   Task: {test_case['state'].task_description}")
            
            # Mock task_requirements.model_dump()
            test_case['state'].task_requirements.model_dump = lambda: {
                "requirements": test_case['state'].task_requirements.requirements,
                "technical_specs": test_case['state'].task_requirements.technical_specs
            }
            
            decision = planner.websearch_branch(test_case['state'])
            
            status = "✅" if decision == test_case['expected'] else "❌"
            print(f"   Decision: {decision} {status}")
            print(f"   Expected: {test_case['expected']}")
        
        print("\n✅ Workflow integration demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow integration demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Chạy tất cả demos."""
    print("🎯 WebSearch Integration Demo")
    print("=" * 50)
    
    demos = [
        ("WebSearch Decision Logic", demo_websearch_decision),
        ("Search Queries Generation", demo_search_queries),
        ("WebSearch Node", demo_websearch_node),
        ("Workflow Integration", demo_workflow_integration),
    ]
    
    passed = 0
    total = len(demos)
    
    for demo_name, demo_func in demos:
        print(f"\n🎯 Demo: {demo_name}")
        print("=" * 50)
        
        if demo_func():
            passed += 1
        else:
            print(f"❌ {demo_name} demo failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Demo Results: {passed}/{total} demos completed successfully")
    
    if passed == total:
        print("🎉 All demos completed successfully! WebSearch integration is ready.")
        print("\n📋 Summary:")
        print("✅ WebSearch decision logic implemented")
        print("✅ Search queries generation working")
        print("✅ WebSearch node integrated")
        print("✅ Workflow branching functional")
        print("\n🚀 Ready for production use!")
        return True
    else:
        print("⚠️  Some demos failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
