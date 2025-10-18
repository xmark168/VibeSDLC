"""
Test Planner Agent với WebSearch Integration

Test workflow của Planner Agent với websearch node.
"""

import os
import pytest
from unittest.mock import patch, Mock

from app.agents.developer.planner.agent import PlannerAgent
from app.agents.developer.planner.state import PlannerState


class TestPlannerWebSearchWorkflow:
    """Test integration của websearch vào planner workflow."""
    
    def setup_method(self):
        """Setup cho mỗi test."""
        self.planner = PlannerAgent(
            model="gpt-4o-mini",
            session_id="test_session",
            user_id="test_user"
        )
    
    @patch('app.agents.developer.planner.nodes.websearch.tavily_search_tool')
    @patch('app.agents.developer.planner.nodes.parse_task.ChatOpenAI')
    def test_workflow_with_websearch(self, mock_llm_class, mock_search_tool):
        """Test workflow khi websearch được thực hiện."""
        # Mock LLM response cho parse_task
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = '''```json
        {
            "functional_requirements": ["Implement JWT authentication", "Add refresh token support"],
            "acceptance_criteria": ["Users can login with JWT", "Tokens can be refreshed"],
            "business_rules": {"session_timeout": "24 hours"},
            "technical_specs": {"framework": "FastAPI", "auth_method": "JWT"},
            "assumptions": ["Using PostgreSQL database"],
            "constraints": ["Must be secure", "Must follow OAuth2 standards"]
        }
        ```'''
        mock_llm_class.return_value = mock_llm
        
        # Mock search results
        mock_search_tool.return_value = '''
        {
            "status": "success",
            "query": "JWT authentication implementation guide",
            "results": [
                {
                    "title": "JWT Authentication Best Practices",
                    "url": "https://example.com/jwt-guide",
                    "content": "JWT tokens should be stored securely and have proper expiration times...",
                    "score": 0.95
                }
            ],
            "search_time": 1.2
        }
        '''
        
        # Mock other nodes để focus vào websearch
        with patch('app.agents.developer.planner.nodes.initialize.initialize') as mock_init, \
             patch('app.agents.developer.planner.nodes.initialize_sandbox.initialize_sandbox') as mock_sandbox, \
             patch('app.agents.developer.planner.nodes.analyze_codebase.analyze_codebase') as mock_analyze, \
             patch('app.agents.developer.planner.nodes.map_dependencies.map_dependencies') as mock_deps, \
             patch('app.agents.developer.planner.nodes.generate_plan.generate_plan') as mock_plan, \
             patch('app.agents.developer.planner.nodes.validate_plan.validate_plan') as mock_validate, \
             patch('app.agents.developer.planner.nodes.finalize.finalize') as mock_finalize:
            
            # Setup mock returns để workflow có thể tiếp tục
            def pass_through(state):
                return state
            
            mock_init.side_effect = pass_through
            mock_sandbox.side_effect = pass_through
            mock_analyze.side_effect = pass_through
            mock_deps.side_effect = pass_through
            mock_plan.side_effect = pass_through
            
            def validate_pass(state):
                state.can_proceed = True
                return state
            mock_validate.side_effect = validate_pass
            mock_finalize.side_effect = pass_through
            
            # Run planner với task cần websearch
            result = self.planner.run(
                task_description="Implement JWT authentication with best practices and security",
                codebase_context="",  # Empty context để trigger websearch
                thread_id="test_thread"
            )
        
        # Verify websearch được gọi
        mock_search_tool.assert_called()
        
        # Verify workflow completed
        assert result is not None
    
    @patch('app.agents.developer.planner.nodes.parse_task.ChatOpenAI')
    def test_workflow_skip_websearch(self, mock_llm_class):
        """Test workflow khi websearch được skip."""
        # Mock LLM response cho parse_task
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = '''```json
        {
            "functional_requirements": ["Fix typo in user model"],
            "acceptance_criteria": ["Typo is corrected"],
            "business_rules": {},
            "technical_specs": {"file": "models/user.py", "line": "25"},
            "assumptions": [],
            "constraints": ["Maintain existing functionality"]
        }
        ```'''
        mock_llm_class.return_value = mock_llm
        
        # Mock other nodes
        with patch('app.agents.developer.planner.nodes.initialize.initialize') as mock_init, \
             patch('app.agents.developer.planner.nodes.initialize_sandbox.initialize_sandbox') as mock_sandbox, \
             patch('app.agents.developer.planner.nodes.analyze_codebase.analyze_codebase') as mock_analyze, \
             patch('app.agents.developer.planner.nodes.map_dependencies.map_dependencies') as mock_deps, \
             patch('app.agents.developer.planner.nodes.generate_plan.generate_plan') as mock_plan, \
             patch('app.agents.developer.planner.nodes.validate_plan.validate_plan') as mock_validate, \
             patch('app.agents.developer.planner.nodes.finalize.finalize') as mock_finalize:
            
            def pass_through(state):
                return state
            
            mock_init.side_effect = pass_through
            mock_sandbox.side_effect = pass_through
            mock_analyze.side_effect = pass_through
            mock_deps.side_effect = pass_through
            mock_plan.side_effect = pass_through
            
            def validate_pass(state):
                state.can_proceed = True
                return state
            mock_validate.side_effect = validate_pass
            mock_finalize.side_effect = pass_through
            
            # Run planner với task đơn giản
            result = self.planner.run(
                task_description="Fix typo in user model field name",
                codebase_context="Well-documented FastAPI app with clear user models",
                thread_id="test_thread"
            )
        
        # Verify workflow completed
        assert result is not None
    
    def test_websearch_branch_logic(self):
        """Test logic của websearch_branch method."""
        # Test case 1: Should search
        state1 = PlannerState(
            task_description="Implement OAuth2 authentication with best practices",
            codebase_context="",
            task_requirements=Mock()
        )
        state1.task_requirements.model_dump.return_value = {
            "requirements": ["OAuth2", "Authentication", "Security"],
            "technical_specs": {}
        }
        
        with patch('app.agents.developer.planner.tools.tavily_search.should_perform_websearch') as mock_should_search:
            mock_should_search.return_value = (True, "Need external information")
            
            decision = self.planner.websearch_branch(state1)
            assert decision == "websearch"
        
        # Test case 2: Should skip
        state2 = PlannerState(
            task_description="Fix simple bug",
            codebase_context="Well-documented codebase",
            task_requirements=Mock()
        )
        state2.task_requirements.model_dump.return_value = {
            "requirements": ["Fix bug"],
            "technical_specs": {"file": "models/user.py"}
        }
        
        with patch('app.agents.developer.planner.tools.tavily_search.should_perform_websearch') as mock_should_search:
            mock_should_search.return_value = (False, "Sufficient information available")
            
            decision = self.planner.websearch_branch(state2)
            assert decision == "analyze_codebase"


class TestWebSearchConfiguration:
    """Test configuration và setup của websearch."""
    
    def test_tavily_api_key_check(self):
        """Test kiểm tra TAVILY_API_KEY."""
        # Test với API key
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test-key'}):
            from app.agents.developer.planner.tools.tavily_search import tavily_search_tool
            
            with patch('app.agents.developer.planner.tools.tavily_search.TavilySearchResults') as mock_tavily:
                mock_search_instance = Mock()
                mock_search_instance.invoke.return_value = []
                mock_tavily.return_value = mock_search_instance
                
                result = tavily_search_tool("test query")
                assert '"status": "success"' in result
        
        # Test không có API key
        with patch.dict(os.environ, {}, clear=True):
            from app.agents.developer.planner.tools.tavily_search import tavily_search_tool
            
            result = tavily_search_tool("test query")
            assert '"status": "error"' in result
            assert "TAVILY_API_KEY not found" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
