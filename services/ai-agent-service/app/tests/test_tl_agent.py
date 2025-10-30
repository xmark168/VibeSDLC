"""Tests for Team Leader Agent.

Test natural language classification với Vietnamese và English.
"""

import pytest
from app.agents.team_leader.tl_agent import TeamLeaderAgent, RoutingDecision


def safe_print(msg):
    """Print with encoding error handling for Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Replace Vietnamese text with placeholder
        print(msg.encode('ascii', 'replace').decode('ascii'))


@pytest.fixture
def tl_agent():
    """Create TL Agent instance for testing."""
    return TeamLeaderAgent(session_id="test_session", user_id="test_user")


class TestTeamLeaderAgent:
    """Test cases for Team Leader Agent classification."""

    def test_po_agent_routing_vietnamese(self, tl_agent):
        """Test routing to PO Agent với Vietnamese natural language."""
        test_cases = [
            "Tôi muốn làm một trang web bán quần áo online",
            "Tạo cho tôi một app quản lý công việc",
            "Muốn làm website bán hàng",
            "Thêm tính năng thanh toán vào app",
            "App cần có những tính năng gì?",
            "Làm tính năng nào trước đây?",
            "Tôi có ý tưởng về sản phẩm mới",
            "Muốn làm app mobile cho nhà hàng",
        ]

        for message in test_cases:
            result = tl_agent.classify(message)
            assert result.agent == "po", f"Failed for: {message}"
            assert result.confidence > 0.7, f"Low confidence for: {message}"
            safe_print(f"[OK] PO -> {result.agent} ({result.confidence:.2f})")

    def test_scrum_master_routing_vietnamese(self, tl_agent):
        """Test routing to Scrum Master với Vietnamese."""
        test_cases = [
            "Dự án làm đến đâu rồi?",
            "Bao giờ thì xong?",
            "Tại sao team làm chậm vậy?",
            "Làm thế nào để nhanh hơn?",
            "Có vấn đề gì đang gặp không?",
            "Cần bao lâu để hoàn thành?",
            "Team làm việc có hiệu quả không?",
            "Tiến độ như thế nào?",
        ]

        for message in test_cases:
            result = tl_agent.classify(message)
            assert result.agent == "scrum_master", f"Failed for: {message}"
            assert result.confidence > 0.7, f"Low confidence for: {message}"
            safe_print(f"[OK] SM: {message} -> {result.agent} ({result.confidence:.2f})")

    def test_developer_routing_vietnamese(self, tl_agent):
        """Test routing to Developer Agent với Vietnamese."""
        test_cases = [
            "Làm sao để website chạy nhanh hơn?",
            "Có thể tích hợp với Facebook không?",
            "Dữ liệu được lưu ở đâu?",
            "Làm sao để app không bị hack?",
            "Website có thể chịu được 10,000 người không?",
            "Kết nối với hệ thống payment như thế nào?",
            "App có thể hoạt động offline không?",
        ]

        for message in test_cases:
            result = tl_agent.classify(message)
            assert result.agent == "developer", f"Failed for: {message}"
            assert result.confidence > 0.7, f"Low confidence for: {message}"
            safe_print(f"[OK] Dev: {message} -> {result.agent} ({result.confidence:.2f})")

    def test_tester_routing_vietnamese(self, tl_agent):
        """Test routing to Tester Agent với Vietnamese."""
        test_cases = [
            "Trang web bị lỗi",
            "Không đăng nhập được",
            "Nút này không hoạt động",
            "App có lỗi gì không?",
            "Làm sao biết không có bug?",
            "Kiểm tra giúp tôi xem có lỗi không",
            "Chức năng thanh toán không chạy",
            "Sản phẩm có chất lượng tốt không?",
        ]

        for message in test_cases:
            result = tl_agent.classify(message)
            assert result.agent == "tester", f"Failed for: {message}"
            assert result.confidence > 0.7, f"Low confidence for: {message}"
            safe_print(f"[OK] Tester: {message} -> {result.agent} ({result.confidence:.2f})")

    def test_conversation_context(self, tl_agent):
        """Test conversation history tracking."""
        # Turn 1: Create project
        result1 = tl_agent.classify("Tôi muốn làm app bán hàng")
        assert result1.agent == "po"

        # Turn 2: Ask timeline (context-aware)
        result2 = tl_agent.classify("Bao giờ xong?")
        # Với context, nên route to SM
        assert result2.agent == "scrum_master"

        safe_print(f"[OK] Context test passed: 'Bao giờ xong?' -> {result2.agent}")

    def test_english_support(self, tl_agent):
        """Test English language support."""
        test_cases = [
            ("I want to create a website", "po"),
            ("When will it be done?", "scrum_master"),
            ("How does it work?", "developer"),
            ("The login page is broken", "tester"),
        ]

        for message, expected_agent in test_cases:
            result = tl_agent.classify(message)
            assert result.agent == expected_agent, f"Failed for: {message}"
            safe_print(f"[OK] EN: {message} -> {result.agent}")

    def test_fallback_on_ambiguous(self, tl_agent):
        """Test fallback behavior với ambiguous messages."""
        ambiguous_messages = [
            "Xin chào",
            "Help me",
            "Tôi có câu hỏi",
        ]

        for message in ambiguous_messages:
            result = tl_agent.classify(message)
            # Should default to PO or have low confidence
            assert result.agent in ["po", "scrum_master", "developer", "tester"]
            safe_print(f"[OK] Ambiguous: {message} -> {result.agent} (confidence: {result.confidence:.2f})")

    def test_pydantic_output(self, tl_agent):
        """Test Pydantic output structure."""
        result = tl_agent.classify("Tạo website")

        # Check all required fields
        assert hasattr(result, "agent")
        assert hasattr(result, "confidence")
        assert hasattr(result, "reasoning")
        assert hasattr(result, "user_intent")

        # Check types
        assert isinstance(result.agent, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.reasoning, str)
        assert isinstance(result.user_intent, str)

        # Check constraints
        assert result.agent in ["po", "scrum_master", "developer", "tester"]
        assert 0.0 <= result.confidence <= 1.0

        safe_print(f"[OK] Pydantic validation passed")

    def test_run_method_compatibility(self, tl_agent):
        """Test run() method compatibility với other agents."""
        result = tl_agent.run("Tạo app mới")

        # Check dict output
        assert isinstance(result, dict)
        assert "agent_name" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert "user_intent" in result

        safe_print(f"[OK] run() method compatibility passed")

    def test_conversation_history_tracking(self, tl_agent):
        """Test conversation history storage."""
        # Clear history first
        tl_agent.clear_history()

        # Send messages
        tl_agent.classify("Tạo app")
        tl_agent.classify("Thêm feature")

        # Check history
        history = tl_agent.get_conversation_history()
        assert len(history) > 0
        assert any(msg.get("role") == "user" for msg in history)

        safe_print(f"[OK] History tracking: {len(history)} messages")

    def test_accuracy_benchmark(self, tl_agent):
        """Benchmark accuracy với comprehensive test set."""
        test_set = [
            # PO cases (15)
            ("Tôi muốn làm website", "po"),
            ("Tạo app mobile", "po"),
            ("Thêm tính năng mới", "po"),
            ("Cần những gì để start", "po"),
            ("Lập kế hoạch sản phẩm", "po"),
            ("Product backlog", "po"),
            ("User stories", "po"),
            ("Tính năng nào ưu tiên", "po"),
            ("Roadmap sản phẩm", "po"),
            ("Vision cho app", "po"),
            ("Requirements là gì", "po"),
            ("Làm app bán hàng", "po"),
            ("Website ecommerce", "po"),
            ("Ứng dụng quản lý", "po"),
            ("Hệ thống CRM", "po"),

            # SM cases (10)
            ("Tiến độ thế nào", "scrum_master"),
            ("Bao giờ xong", "scrum_master"),
            ("Team làm chậm", "scrum_master"),
            ("Sprint velocity", "scrum_master"),
            ("Có blocker không", "scrum_master"),
            ("Cải thiện tốc độ", "scrum_master"),
            ("Đánh giá hiệu suất", "scrum_master"),
            ("Timeline dự án", "scrum_master"),
            ("Khi nào release", "scrum_master"),
            ("Progress report", "scrum_master"),

            # Dev cases (10)
            ("Làm sao tích hợp API", "developer"),
            ("Website chạy nhanh không", "developer"),
            ("Kiến trúc hệ thống", "developer"),
            ("Database nào tốt", "developer"),
            ("Security thế nào", "developer"),
            ("Scalability", "developer"),
            ("Deploy lên server", "developer"),
            ("Technical feasibility", "developer"),
            ("Performance optimization", "developer"),
            ("Infrastructure setup", "developer"),

            # Tester cases (10)
            ("App bị lỗi", "tester"),
            ("Login không được", "tester"),
            ("Bug report", "tester"),
            ("Kiểm tra chất lượng", "tester"),
            ("Test cases", "tester"),
            ("Có bug gì không", "tester"),
            ("Quality assurance", "tester"),
            ("Tính năng không chạy", "tester"),
            ("Automation testing", "tester"),
            ("Regression test", "tester"),
        ]

        correct = 0
        total = len(test_set)

        for message, expected_agent in test_set:
            result = tl_agent.classify(message)
            if result.agent == expected_agent:
                correct += 1
            else:
                safe_print(f"[X] Miss: '{message}' -> {result.agent} (expected: {expected_agent})")

        accuracy = correct / total
        safe_print(f"\n[Stats] Accuracy: {accuracy:.1%} ({correct}/{total})")

        # Assert minimum accuracy threshold
        assert accuracy >= 0.85, f"Accuracy too low: {accuracy:.1%}"


# Run tests if executed directly
if __name__ == "__main__":
    print("=" * 80)
    print("Team Leader Agent - Comprehensive Test Suite")
    print("=" * 80)

    agent = TeamLeaderAgent(session_id="test", user_id="test")

    print("\n1. Testing PO routing...")
    test = TestTeamLeaderAgent()
    test.test_po_agent_routing_vietnamese(agent)

    print("\n2. Testing SM routing...")
    test.test_scrum_master_routing_vietnamese(agent)

    print("\n3. Testing Developer routing...")
    test.test_developer_routing_vietnamese(agent)

    print("\n4. Testing Tester routing...")
    test.test_tester_routing_vietnamese(agent)

    print("\n5. Testing accuracy...")
    test.test_accuracy_benchmark(agent)

    print("\n[OK] All tests completed!")
