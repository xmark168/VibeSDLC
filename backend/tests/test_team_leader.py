"""Test Team Leader Agent with various contexts and scenarios.

Tests cover:
1. Routing decisions (DELEGATE, RESPOND, CONVERSATION)
2. Delegation to different specialists (BA, Developer, Tester)
3. Vietnamese and English messages
4. Quick responses (greetings, acknowledgments)
5. Conversational scenarios (questions, chitchat)
6. Edge cases and error handling
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.team_leader.src.prompts import (
    parse_llm_decision,
    extract_role,
    build_system_prompt,
    build_user_prompt,
)
from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.nodes import router, delegate, respond, conversational


# =============================================================================
# TEST CASES DATA
# =============================================================================

# Delegation scenarios - should route to specialists
DELEGATE_TO_BA_CASES = [
    # Vietnamese
    ("tạo website bán hàng online", "business_analyst"),
    ("xây dựng app quản lý kho", "business_analyst"),
    ("phân tích yêu cầu cho hệ thống CRM", "business_analyst"),
    ("mình cần làm một trang landing page", "business_analyst"),
    ("thiết kế hệ thống đặt phòng khách sạn", "business_analyst"),
    ("viết PRD cho tính năng login", "business_analyst"),
    # English
    ("build an e-commerce platform", "business_analyst"),
    ("create a mobile app for food delivery", "business_analyst"),
    ("I need a new feature for user management", "business_analyst"),
    ("design a booking system", "business_analyst"),
]

DELEGATE_TO_DEVELOPER_CASES = [
    # Vietnamese
    ("implement story #123", "developer"),
    ("fix bug login không được", "developer"),
    ("code tính năng thanh toán", "developer"),
    ("sửa lỗi crash app", "developer"),
    ("implement API endpoint", "developer"),
    # English
    ("implement the payment feature", "developer"),
    ("fix the authentication bug", "developer"),
    ("develop the user profile page", "developer"),
    ("refactor the database queries", "developer"),
]

DELEGATE_TO_TESTER_CASES = [
    # Vietnamese
    ("test tính năng đăng nhập", "tester"),
    ("tạo test plan cho module thanh toán", "tester"),
    ("QA cho release v2.0", "tester"),
    ("kiểm tra lỗi regression", "tester"),
    # English
    ("test the payment module", "tester"),
    ("create test cases for login", "tester"),
    ("QA the new features", "tester"),
    ("validate the API responses", "tester"),
]

# Quick response scenarios - should handle directly
RESPOND_CASES = [
    "cảm ơn",
    "thanks",
    "ok",
    "được rồi",
    "tuyệt vời",
    "got it",
    "bye",
    "tạm biệt",
]

# Conversational scenarios - should handle with personality
CONVERSATION_CASES = [
    # Greetings
    "chào bạn",
    "hello",
    "hi team leader",
    "xin chào",
    # Questions
    "AI là gì?",
    "what is machine learning?",
    "Kanban hoạt động như thế nào?",
    "how does agile work?",
    # Chitchat
    "hôm nay trời đẹp quá",
    "mình đang stress quá",
    "bạn có khỏe không?",
    # Knowledge queries
    "giải thích WIP limit",
    "what is technical debt?",
    "cho mình biết về microservices",
]


# =============================================================================
# UNIT TESTS - parse_llm_decision
# =============================================================================

class TestParseLLMDecision:
    """Test LLM response parsing."""
    
    def test_parse_valid_delegate_json(self):
        """Test parsing valid DELEGATE JSON response."""
        response = '''
        {
            "action": "DELEGATE",
            "target_role": "business_analyst",
            "message": "Mình sẽ chuyển cho @Business Analyst nhé!",
            "reason": "new_feature_request"
        }
        '''
        result = parse_llm_decision(response)
        
        assert result["action"] == "DELEGATE"
        assert result["target_role"] == "business_analyst"
        assert "@Business Analyst" in result["message"]
        assert result["reason"] == "new_feature_request"
    
    def test_parse_valid_respond_json(self):
        """Test parsing valid RESPOND JSON response."""
        response = '''
        {
            "action": "RESPOND",
            "message": "Không có chi! 👍",
            "reason": "acknowledgment"
        }
        '''
        result = parse_llm_decision(response)
        
        assert result["action"] == "RESPOND"
        assert "👍" in result["message"]
    
    def test_parse_valid_conversation_json(self):
        """Test parsing valid CONVERSATION JSON response."""
        response = '''
        {
            "action": "CONVERSATION",
            "message": "",
            "reason": "greeting_detected"
        }
        '''
        result = parse_llm_decision(response)
        
        assert result["action"] == "CONVERSATION"
    
    def test_parse_json_with_nested_content(self):
        """Test parsing JSON with nested structures."""
        response = '''
        Here's my analysis:
        {
            "action": "DELEGATE",
            "target_role": "developer",
            "message": "Chuyển cho @Developer implement",
            "reason": "implementation_task",
            "metadata": {"priority": "high"}
        }
        '''
        result = parse_llm_decision(response)
        
        assert result["action"] == "DELEGATE"
        assert result["target_role"] == "developer"
    
    def test_parse_fallback_delegate(self):
        """Test fallback parsing when DELEGATE keyword found."""
        response = "I think we should DELEGATE this to the business analyst"
        result = parse_llm_decision(response)
        
        assert result["action"] == "DELEGATE"
        assert "fallback" in result["reason"]
    
    def test_parse_fallback_conversation(self):
        """Test fallback parsing when CONVERSATION keyword found."""
        response = "This seems like a CONVERSATION topic"
        result = parse_llm_decision(response)
        
        assert result["action"] == "CONVERSATION"
    
    def test_parse_fallback_respond(self):
        """Test fallback to RESPOND when no keywords found."""
        response = "Sure, I can help with that!"
        result = parse_llm_decision(response)
        
        assert result["action"] == "RESPOND"
    
    def test_parse_malformed_json(self):
        """Test handling of malformed JSON."""
        response = '{"action": "DELEGATE", broken json'
        result = parse_llm_decision(response)
        
        # Should fallback gracefully
        assert "action" in result
        assert "message" in result


class TestExtractRole:
    """Test role extraction from text."""
    
    def test_extract_business_analyst(self):
        assert extract_role("send to business_analyst") == "business_analyst"
        assert extract_role("Business Analyst will handle") == "business_analyst"
    
    def test_extract_developer(self):
        assert extract_role("developer should implement") == "developer"
        assert extract_role("assign to Developer") == "developer"
    
    def test_extract_tester(self):
        assert extract_role("tester needs to QA") == "tester"
        assert extract_role("send to Tester") == "tester"
    
    def test_extract_default(self):
        """Default to business_analyst when no role found."""
        assert extract_role("unknown role here") == "business_analyst"


# =============================================================================
# UNIT TESTS - Prompts
# =============================================================================

class TestPromptBuilding:
    """Test prompt building utilities."""
    
    def test_build_system_prompt_without_agent(self):
        """Test system prompt with no agent (defaults)."""
        prompt = build_system_prompt(None)
        
        assert "Team Leader" in prompt
        assert "ROUTING" in prompt or "routing" in prompt.lower()
    
    def test_build_system_prompt_with_agent(self):
        """Test system prompt with agent personality."""
        mock_agent = MagicMock()
        mock_agent.agent_model.human_name = "Minh"
        mock_agent.agent_model.role_type = "team_leader"
        mock_agent.agent_model.personality_traits = ["friendly", "professional"]
        mock_agent.agent_model.communication_style = "warm and supportive"
        mock_agent.agent_model.persona_metadata = {
            "role": "Team Leader & Agile Coach",
            "goal": "Help team succeed",
            "backstory": "10 years experience",
            "tone": "Friendly Vietnamese"
        }
        
        prompt = build_system_prompt(mock_agent)
        
        assert "Minh" in prompt
        assert "friendly" in prompt or "professional" in prompt
    
    def test_build_user_prompt(self):
        """Test user prompt building."""
        prompt = build_user_prompt(
            user_message="tạo website bán hàng",
            name="Minh",
            conversation_history="User: chào\nAssistant: Chào bạn!",
            user_preferences="- Language: Vietnamese"
        )
        
        assert "tạo website bán hàng" in prompt
        assert "conversation" in prompt.lower() or "CONVERSATION" in prompt


# =============================================================================
# INTEGRATION TESTS - Router Node (Mocked LLM)
# =============================================================================

class TestRouterNode:
    """Test router node with mocked LLM responses."""
    
    @pytest.fixture
    def base_state(self):
        """Create base state for testing."""
        return {
            "messages": [],
            "user_message": "",
            "user_id": str(uuid4()),
            "project_id": str(uuid4()),
            "task_id": str(uuid4()),
            "conversation_history": "",
            "user_preferences": "",
            "action": None,
            "target_role": None,
            "message": None,
            "reason": None,
            "confidence": None,
        }
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock agent."""
        agent = MagicMock()
        agent.name = "TestLeader"
        agent.agent_model.human_name = "Test"
        agent.agent_model.role_type = "team_leader"
        agent.agent_model.personality_traits = ["friendly"]
        agent.agent_model.communication_style = "professional"
        agent.agent_model.persona_metadata = {}
        agent.track_llm_generation = MagicMock()
        return agent
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_message,expected_role", DELEGATE_TO_BA_CASES)
    async def test_router_delegates_to_ba(self, base_state, mock_agent, user_message, expected_role):
        """Test router delegates new feature requests to BA."""
        base_state["user_message"] = user_message
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = f'''
        {{
            "action": "DELEGATE",
            "target_role": "{expected_role}",
            "message": "Mình sẽ chuyển cho @Business Analyst nhé!",
            "reason": "new_feature_request"
        }}
        '''
        
        with patch('app.agents.team_leader.src.nodes.ChatOpenAI') as mock_llm:
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "DELEGATE"
            assert result["target_role"] == expected_role
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_message,expected_role", DELEGATE_TO_DEVELOPER_CASES)
    async def test_router_delegates_to_developer(self, base_state, mock_agent, user_message, expected_role):
        """Test router delegates implementation tasks to Developer."""
        base_state["user_message"] = user_message
        
        mock_response = MagicMock()
        mock_response.content = f'''
        {{
            "action": "DELEGATE",
            "target_role": "{expected_role}",
            "message": "Chuyển cho @Developer implement nhé!",
            "reason": "implementation_task"
        }}
        '''
        
        with patch('app.agents.team_leader.src.nodes.ChatOpenAI') as mock_llm:
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "DELEGATE"
            assert result["target_role"] == expected_role
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_message", RESPOND_CASES)
    async def test_router_responds_to_acknowledgments(self, base_state, mock_agent, user_message):
        """Test router handles acknowledgments directly."""
        base_state["user_message"] = user_message
        
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "action": "RESPOND",
            "message": "Không có chi! 👍",
            "reason": "acknowledgment"
        }
        '''
        
        with patch('app.agents.team_leader.src.nodes.ChatOpenAI') as mock_llm:
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "RESPOND"
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_message", CONVERSATION_CASES)
    async def test_router_handles_conversation(self, base_state, mock_agent, user_message):
        """Test router routes to conversation node."""
        base_state["user_message"] = user_message
        
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "action": "CONVERSATION",
            "message": "",
            "reason": "conversation_detected"
        }
        '''
        
        with patch('app.agents.team_leader.src.nodes.ChatOpenAI') as mock_llm:
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "CONVERSATION"


# =============================================================================
# INTEGRATION TESTS - Delegate Node
# =============================================================================

class TestDelegateNode:
    """Test delegate node functionality."""
    
    @pytest.fixture
    def delegate_state(self):
        """Create state for delegation testing."""
        return {
            "messages": [],
            "user_message": "tạo website bán hàng",
            "user_id": str(uuid4()),
            "project_id": str(uuid4()),
            "task_id": str(uuid4()),
            "target_role": "business_analyst",
            "message": "Mình sẽ chuyển cho @Business Analyst nhé! 🚀",
            "reason": "new_feature_request",
            "action": "DELEGATE",
        }
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock agent with async methods."""
        agent = MagicMock()
        agent.name = "TestLeader"
        agent.message_user = AsyncMock()
        agent.delegate_to_role = AsyncMock()
        agent.create_span = MagicMock(return_value=MagicMock())
        agent.track_event = MagicMock()
        return agent
    
    @pytest.mark.asyncio
    async def test_delegate_sends_message_with_mention(self, delegate_state, mock_agent):
        """Test delegate node sends message with @mention."""
        result = await delegate(delegate_state, mock_agent)
        
        # Verify message_user was called with @mention
        mock_agent.message_user.assert_called_once()
        call_args = mock_agent.message_user.call_args
        message = call_args[0][1]  # Second positional arg is the message
        
        assert "@Business Analyst" in message or "@" in message
    
    @pytest.mark.asyncio
    async def test_delegate_calls_delegate_to_role(self, delegate_state, mock_agent):
        """Test delegate node calls delegate_to_role."""
        await delegate(delegate_state, mock_agent)
        
        mock_agent.delegate_to_role.assert_called_once()
        call_kwargs = mock_agent.delegate_to_role.call_args[1]
        
        assert call_kwargs["target_role"] == "business_analyst"
    
    @pytest.mark.asyncio
    async def test_delegate_uses_llm_message_when_available(self, delegate_state, mock_agent):
        """Test delegate uses LLM-generated message."""
        delegate_state["message"] = "Custom LLM message for @Business Analyst"
        
        await delegate(delegate_state, mock_agent)
        
        call_args = mock_agent.message_user.call_args[0]
        assert "Custom LLM message" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_delegate_fallback_message(self, delegate_state, mock_agent):
        """Test delegate uses fallback when no LLM message."""
        delegate_state["message"] = None
        delegate_state["target_role"] = "developer"
        
        await delegate(delegate_state, mock_agent)
        
        call_args = mock_agent.message_user.call_args[0]
        assert "@Developer" in call_args[1]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_role,expected_mention", [
        ("business_analyst", "@Business Analyst"),
        ("developer", "@Developer"),
        ("tester", "@Tester"),
        ("architect", "@Architect"),
    ])
    async def test_delegate_correct_mention_per_role(self, delegate_state, mock_agent, target_role, expected_mention):
        """Test delegate uses correct @mention for each role."""
        delegate_state["message"] = None
        delegate_state["target_role"] = target_role
        
        await delegate(delegate_state, mock_agent)
        
        call_args = mock_agent.message_user.call_args[0]
        assert expected_mention in call_args[1]


# =============================================================================
# INTEGRATION TESTS - Respond Node
# =============================================================================

class TestRespondNode:
    """Test respond node functionality."""
    
    @pytest.mark.asyncio
    async def test_respond_sends_message(self):
        """Test respond node sends message to user."""
        state = {
            "message": "Không có chi! 👍",
            "action": "RESPOND",
        }
        
        mock_agent = MagicMock()
        mock_agent.message_user = AsyncMock()
        
        result = await respond(state, mock_agent)
        
        mock_agent.message_user.assert_called_once_with("response", "Không có chi! 👍")
        assert result["action"] == "RESPOND"
    
    @pytest.mark.asyncio
    async def test_respond_default_message(self):
        """Test respond with default message."""
        state = {"action": "RESPOND"}
        
        mock_agent = MagicMock()
        mock_agent.message_user = AsyncMock()
        
        await respond(state, mock_agent)
        
        call_args = mock_agent.message_user.call_args[0]
        assert call_args[1] == "How can I help you?"


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_parse_empty_response(self):
        """Test parsing empty response."""
        result = parse_llm_decision("")
        assert "action" in result
    
    def test_parse_none_response(self):
        """Test parsing None-like response."""
        result = parse_llm_decision("null")
        assert "action" in result
    
    @pytest.mark.asyncio
    async def test_router_handles_llm_error(self):
        """Test router handles LLM errors gracefully."""
        state = {
            "messages": [],
            "user_message": "test message",
            "user_id": str(uuid4()),
            "project_id": str(uuid4()),
            "task_id": str(uuid4()),
            "conversation_history": "",
            "user_preferences": "",
        }
        
        mock_agent = MagicMock()
        mock_agent.name = "Test"
        mock_agent.agent_model.human_name = "Test"
        mock_agent.agent_model.role_type = "team_leader"
        mock_agent.agent_model.personality_traits = []
        mock_agent.agent_model.communication_style = ""
        mock_agent.agent_model.persona_metadata = {}
        
        with patch('app.agents.team_leader.src.nodes.ChatOpenAI') as mock_llm:
            mock_llm.return_value.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))
            
            result = await router(state, mock_agent)
            
            # Should return RESPOND action on error
            assert result["action"] == "RESPOND"
            assert "error" in result.get("reason", "").lower()
    
    @pytest.mark.asyncio
    async def test_delegate_without_agent(self):
        """Test delegate node without agent (no-op)."""
        state = {
            "target_role": "business_analyst",
            "message": "Test",
            "user_message": "test",
            "project_id": str(uuid4()),
            "task_id": str(uuid4()),
        }
        
        result = await delegate(state, agent=None)
        
        assert result["action"] == "DELEGATE"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
