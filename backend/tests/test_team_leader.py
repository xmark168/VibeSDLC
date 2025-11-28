"""Test Team Leader Agent with various contexts and scenarios.

Tests cover:
1. Routing decisions (DELEGATE, RESPOND, CONVERSATION, STATUS_CHECK)
2. Delegation to different specialists (BA, Developer, Tester)
3. Vietnamese and English messages
4. Quick responses (greetings, acknowledgments)
5. Conversational scenarios (questions, chitchat)
6. Tool calling (get_board_status, get_active_stories, etc.)
7. WIP limit enforcement
8. Edge cases and error handling
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.team_leader.src.schemas import RoutingDecision
from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.nodes import (
    router, delegate, respond, conversational, status_check,
    ROLE_TO_WIP_COLUMN, build_system_prompt, build_user_prompt,
)

# Delay between API calls to avoid rate limiting (RPM)
API_DELAY = 0.5  # seconds


def delay_for_rate_limit():
    """Add delay between tests to avoid rate limiting."""
    time.sleep(API_DELAY)


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

# Status check scenarios - should call tools and report metrics
STATUS_CHECK_CASES = [
    # Vietnamese
    "tiến độ thế nào?",
    "board status?",
    "còn bao nhiêu stories đang làm?",
    "cho xem WIP hiện tại",
    "throughput tuần này?",
    "có story nào bị block không?",
    # English
    "what's the board status?",
    "how many stories in progress?",
    "show me flow metrics",
    "any blocked items?",
]

# WIP blocked scenarios - should be detected and reported
WIP_BLOCKED_SCENARIOS = [
    ("implement story #123", "developer", "InProgress"),
    ("test feature login", "tester", "Review"),
]


# =============================================================================
# UNIT TESTS - RoutingDecision Schema
# =============================================================================

class TestRoutingDecisionSchema:
    """Test RoutingDecision Pydantic schema validation."""
    
    def test_valid_delegate_decision(self):
        """Test valid DELEGATE decision."""
        decision = RoutingDecision(
            action="DELEGATE",
            target_role="business_analyst",
            message="Mình sẽ chuyển cho @Business Analyst nhé!",
            reason="new_feature_request"
        )
        
        assert decision.action == "DELEGATE"
        assert decision.target_role == "business_analyst"
        assert "@Business Analyst" in decision.message
        assert decision.reason == "new_feature_request"
    
    def test_valid_respond_decision(self):
        """Test valid RESPOND decision."""
        decision = RoutingDecision(
            action="RESPOND",
            message="Không có chi! 👍",
            reason="acknowledgment"
        )
        
        assert decision.action == "RESPOND"
        assert decision.target_role is None
        assert "👍" in decision.message
    
    def test_valid_conversation_decision(self):
        """Test valid CONVERSATION decision."""
        decision = RoutingDecision(
            action="CONVERSATION",
            message="",
            reason="greeting_detected"
        )
        
        assert decision.action == "CONVERSATION"
    
    def test_valid_status_check_decision(self):
        """Test valid STATUS_CHECK decision."""
        decision = RoutingDecision(
            action="STATUS_CHECK",
            message="Đây là trạng thái board hiện tại",
            reason="status_query"
        )
        
        assert decision.action == "STATUS_CHECK"
    
    def test_invalid_action_raises_error(self):
        """Test invalid action raises validation error."""
        import pytest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            RoutingDecision(
                action="INVALID_ACTION",
                message="test",
                reason="test"
            )
    
    def test_invalid_target_role_raises_error(self):
        """Test invalid target_role raises validation error."""
        import pytest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            RoutingDecision(
                action="DELEGATE",
                target_role="invalid_role",
                message="test",
                reason="test"
            )
    
    def test_model_dump(self):
        """Test model_dump returns correct dict."""
        decision = RoutingDecision(
            action="DELEGATE",
            target_role="developer",
            message="Chuyển cho @Developer",
            reason="implementation_task"
        )
        
        result = decision.model_dump()
        
        assert result["action"] == "DELEGATE"
        assert result["target_role"] == "developer"
        assert result["message"] == "Chuyển cho @Developer"
        assert result["reason"] == "implementation_task"


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
        """Create base state for testing (simplified state)."""
        return {
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
            "wip_blocked": None,
            "langfuse_handler": None,
        }
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock agent with context for WIP checks."""
        agent = MagicMock()
        agent.name = "TestLeader"
        agent.agent_model.human_name = "Test"
        agent.agent_model.role_type = "team_leader"
        agent.agent_model.personality_traits = ["friendly"]
        agent.agent_model.communication_style = "professional"
        agent.agent_model.persona_metadata = {}
        agent.track_llm_generation = MagicMock()
        # Mock context for WIP checks
        agent.context.get_kanban_context = MagicMock(return_value=(
            {"InProgress": {"limit": 5, "current_stories": 2, "available": 3}},
            {"throughput_per_week": 10},
            {"InProgress": 3, "Review": 2}
        ))
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
    
    @pytest.mark.asyncio
    async def test_router_handles_llm_error(self):
        """Test router handles LLM errors gracefully."""
        state = {
            "user_message": "test message",
            "user_id": str(uuid4()),
            "project_id": str(uuid4()),
            "task_id": str(uuid4()),
            "conversation_history": "",
            "user_preferences": "",
            "langfuse_handler": None,
        }
        
        mock_agent = MagicMock()
        mock_agent.name = "Test"
        mock_agent.agent_model.human_name = "Test"
        mock_agent.agent_model.role_type = "team_leader"
        mock_agent.agent_model.personality_traits = []
        mock_agent.agent_model.communication_style = ""
        mock_agent.agent_model.persona_metadata = {}
        mock_agent.context.get_kanban_context = MagicMock(return_value=({}, {}, {}))
        
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
# TOOL TESTS
# =============================================================================

class TestTools:
    """Test Team Leader tools."""
    
    def test_role_to_wip_column_mapping(self):
        """Test role to WIP column mapping."""
        assert ROLE_TO_WIP_COLUMN["developer"] == "InProgress"
        assert ROLE_TO_WIP_COLUMN["tester"] == "Review"
        assert ROLE_TO_WIP_COLUMN["business_analyst"] is None


class TestStatusCheckNode:
    """Test status_check node functionality."""
    
    @pytest.fixture
    def status_state(self):
        """Create state for status check testing."""
        return {
            "user_message": "tiến độ thế nào?",
            "user_id": str(uuid4()),
            "project_id": str(uuid4()),
            "task_id": str(uuid4()),
            "action": "STATUS_CHECK",
            "message": None,
        }
    
    @pytest.mark.asyncio
    async def test_status_check_calls_tools(self, status_state):
        """Test status_check node calls board tools."""
        mock_agent = MagicMock()
        mock_agent.message_user = AsyncMock()
        
        with patch('app.agents.team_leader.src.nodes.get_board_status') as mock_board, \
             patch('app.agents.team_leader.src.nodes.get_flow_metrics') as mock_flow, \
             patch('app.agents.team_leader.src.nodes.get_active_stories') as mock_stories:
            
            mock_board.invoke.return_value = "Board Status: InProgress 2/5"
            mock_flow.invoke.return_value = "Flow Metrics: Throughput 10/week"
            mock_stories.invoke.return_value = "Active: Story #1, Story #2"
            
            result = await status_check(status_state, mock_agent)
            
            assert result["action"] == "STATUS_CHECK"
            mock_agent.message_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_status_check_handles_error(self, status_state):
        """Test status_check handles errors gracefully."""
        mock_agent = MagicMock()
        mock_agent.message_user = AsyncMock()
        
        with patch('app.agents.team_leader.src.nodes.get_board_status') as mock_board:
            mock_board.invoke.side_effect = Exception("DB Error")
            
            result = await status_check(status_state, mock_agent)
            
            assert result["action"] == "STATUS_CHECK"
            assert "Không thể lấy status" in result["message"]


class TestWIPBlocking:
    """Test WIP limit enforcement."""
    
    @pytest.fixture
    def wip_full_agent(self):
        """Create mock agent with WIP full."""
        agent = MagicMock()
        agent.name = "TestLeader"
        agent.agent_model.human_name = "Test"
        agent.agent_model.role_type = "team_leader"
        agent.agent_model.personality_traits = ["friendly"]
        agent.agent_model.communication_style = "professional"
        agent.agent_model.persona_metadata = {}
        # WIP is FULL
        agent.context.get_kanban_context = MagicMock(return_value=(
            {"InProgress": {"limit": 3, "current_stories": 3, "available": 0}},
            {},
            {"InProgress": 0, "Review": 0}  # No available slots
        ))
        return agent
    
    @pytest.fixture
    def delegate_state(self):
        """Create state for delegation."""
        return {
            "user_message": "implement story #123",
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
            "wip_blocked": None,
            "langfuse_handler": None,
        }
    
    @pytest.mark.asyncio
    async def test_wip_blocked_returns_respond(self, delegate_state, wip_full_agent):
        """Test router blocks delegation when WIP is full."""
        delay_for_rate_limit()
        
        # Mock LLM to return DELEGATE action
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "action": "DELEGATE",
            "target_role": "developer",
            "message": "Chuyển cho @Developer",
            "reason": "implementation"
        }
        '''
        mock_response.tool_calls = None
        
        with patch('app.agents.team_leader.src.nodes._fast_llm') as mock_llm:
            mock_llm.bind_tools.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(delegate_state, wip_full_agent)
            
            # Should be blocked and return RESPOND
            assert result["action"] == "RESPOND"
            assert result["wip_blocked"] == True
            assert "full" in result["message"].lower()


class TestRouterWithTools:
    """Test router with tool calling."""
    
    @pytest.fixture
    def base_state(self):
        """Create base state."""
        return {
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
            "wip_blocked": None,
            "langfuse_handler": None,
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
        agent.context.get_kanban_context = MagicMock(return_value=(
            {"InProgress": {"limit": 5, "available": 3}},
            {},
            {"InProgress": 3, "Review": 2}
        ))
        return agent
    
    @pytest.mark.asyncio
    async def test_router_fast_path_no_tools(self, base_state, mock_agent):
        """Test router takes fast path for greetings (no tools)."""
        delay_for_rate_limit()
        base_state["user_message"] = "xin chào"
        
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "action": "CONVERSATION",
            "message": "",
            "reason": "greeting"
        }
        '''
        mock_response.tool_calls = None  # No tool calls
        
        with patch('app.agents.team_leader.src.nodes._fast_llm') as mock_llm:
            mock_llm.bind_tools.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "CONVERSATION"
            assert result["wip_blocked"] == False
    
# =============================================================================
# INTEGRATION TESTS WITH DELAY
# =============================================================================

class TestIntegrationWithDelay:
    """Integration tests with rate limit delay."""
    
    @pytest.fixture
    def base_state(self):
        return {
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
            "wip_blocked": None,
            "langfuse_handler": None,
        }
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_message", STATUS_CHECK_CASES[:3])  # Limit to avoid rate limits
    async def test_status_check_routing(self, base_state, user_message):
        """Test STATUS_CHECK messages are routed correctly."""
        delay_for_rate_limit()
        base_state["user_message"] = user_message
        
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "action": "STATUS_CHECK",
            "message": "Checking board status...",
            "reason": "status_query"
        }
        '''
        mock_response.tool_calls = None
        
        mock_agent = MagicMock()
        mock_agent.name = "Test"
        mock_agent.agent_model.human_name = "Test"
        mock_agent.agent_model.role_type = "team_leader"
        mock_agent.agent_model.personality_traits = []
        mock_agent.agent_model.communication_style = ""
        mock_agent.agent_model.persona_metadata = {}
        
        with patch('app.agents.team_leader.src.nodes._fast_llm') as mock_llm:
            mock_llm.bind_tools.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router(base_state, mock_agent)
            
            assert result["action"] == "STATUS_CHECK"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
