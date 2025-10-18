"""
Test WebSearch Integration

Test cases để kiểm tra tích hợp Tavily Search vào Planner Agent.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch

from app.agents.developer.planner.state import PlannerState, TaskRequirements, WebSearchResults
from app.agents.developer.planner.nodes.websearch import websearch
from app.agents.developer.planner.tools.tavily_search import (
    should_perform_websearch,
    generate_search_queries,
    tavily_search_tool
)


class TestWebSearchDecision:
    """Test logic quyết định có cần web search hay không."""
    
    def test_should_search_with_indicators(self):
        """Test với task có search indicators."""
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
        
        assert should_search is True
        assert "best practices" in reason.lower()
    
    def test_should_not_search_simple_task(self):
        """Test với task đơn giản không cần search."""
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
        
        assert should_search is False
        assert "sufficient information" in reason.lower()
    
    def test_should_search_no_context(self):
        """Test với task không có codebase context."""
        task_description = "Add new feature"
        task_requirements = {
            "requirements": ["New feature"],
            "technical_specs": {}
        }
        
        should_search, reason = should_perform_websearch(
            task_description=task_description,
            task_requirements=task_requirements,
            codebase_context=""
        )
        
        assert should_search is True
        assert "no codebase context" in reason.lower()


class TestSearchQueries:
    """Test generation của search queries."""
    
    def test_generate_queries_from_task(self):
        """Test tạo queries từ task description."""
        task_description = "Implement JWT authentication with refresh tokens"
        task_requirements = {
            "requirements": ["JWT auth", "Refresh tokens", "Security"],
            "technical_specs": {"framework": "FastAPI", "database": "PostgreSQL"}
        }
        
        queries = generate_search_queries(task_description, task_requirements)
        
        assert len(queries) > 0
        assert len(queries) <= 3  # Limit to 3 queries
        assert any("JWT authentication" in query for query in queries)
        assert any("implementation guide" in query for query in queries)


class TestTavilySearchTool:
    """Test Tavily Search tool wrapper."""
    
    @patch('app.agents.developer.planner.tools.tavily_search.TavilySearchResults')
    def test_tavily_search_success(self, mock_tavily):
        """Test successful search với mock response."""
        # Mock response
        mock_search_instance = Mock()
        mock_search_instance.invoke.return_value = [
            {
                "title": "JWT Authentication Best Practices",
                "url": "https://example.com/jwt-guide",
                "content": "JWT authentication is a secure way to handle user sessions...",
                "score": 0.95
            }
        ]
        mock_tavily.return_value = mock_search_instance
        
        # Set mock API key
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test-key'}):
            result_json = tavily_search_tool(
                query="JWT authentication best practices",
                max_results=3
            )
        
        result = json.loads(result_json)
        
        assert result["status"] == "success"
        assert result["query"] == "JWT authentication best practices"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "JWT Authentication Best Practices"
    
    def test_tavily_search_no_api_key(self):
        """Test search khi không có API key."""
        with patch.dict(os.environ, {}, clear=True):
            result_json = tavily_search_tool(query="test query")
        
        result = json.loads(result_json)
        
        assert result["status"] == "error"
        assert "TAVILY_API_KEY not found" in result["message"]


class TestWebSearchNode:
    """Test WebSearch node integration."""
    
    def test_websearch_node_skip(self):
        """Test websearch node khi skip search."""
        # Tạo state với task đơn giản
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
        with patch('app.agents.developer.planner.nodes.websearch.should_perform_websearch') as mock_should_search:
            mock_should_search.return_value = (False, "Simple task with sufficient context")
            
            result_state = websearch(state)
        
        assert result_state.websearch_results.performed is False
        assert "Simple task" in result_state.websearch_results.reason_for_skip
        assert result_state.current_phase == "analyze_codebase"
        assert result_state.status == "websearch_completed"
    
    @patch('app.agents.developer.planner.nodes.websearch.tavily_search_tool')
    def test_websearch_node_perform_search(self, mock_search_tool):
        """Test websearch node khi thực hiện search."""
        # Mock search results
        mock_search_tool.return_value = json.dumps({
            "status": "success",
            "query": "test query",
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content for implementation",
                    "score": 0.9
                }
            ],
            "search_time": 1.5
        })
        
        # Tạo state với task cần search
        state = PlannerState(
            task_description="Implement advanced authentication with best practices",
            codebase_context="",
            task_requirements=TaskRequirements(
                task_id="TSK-002",
                requirements=["Authentication", "Security", "Best practices"],
                technical_specs={}
            )
        )
        
        # Mock should_perform_websearch để return True
        with patch('app.agents.developer.planner.nodes.websearch.should_perform_websearch') as mock_should_search:
            mock_should_search.return_value = (True, "Need external information")
            
            with patch('app.agents.developer.planner.nodes.websearch.generate_search_queries') as mock_queries:
                mock_queries.return_value = ["test query"]
                
                result_state = websearch(state)
        
        assert result_state.websearch_results.performed is True
        assert len(result_state.websearch_results.results) == 1
        assert result_state.websearch_results.search_time == 1.5
        assert result_state.current_phase == "analyze_codebase"
        assert result_state.status == "websearch_completed"
        
        # Kiểm tra enhanced context
        assert "Web Search Results" in result_state.codebase_context
    
    def test_websearch_node_error_handling(self):
        """Test error handling trong websearch node."""
        state = PlannerState(
            task_description="Test task",
            task_requirements=TaskRequirements(task_id="TSK-003")
        )
        
        # Mock exception trong should_perform_websearch
        with patch('app.agents.developer.planner.nodes.websearch.should_perform_websearch') as mock_should_search:
            mock_should_search.side_effect = Exception("Test error")
            
            result_state = websearch(state)
        
        assert result_state.websearch_results.performed is False
        assert "Error occurred" in result_state.websearch_results.reason_for_skip
        assert result_state.current_phase == "analyze_codebase"  # Vẫn tiếp tục workflow


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
