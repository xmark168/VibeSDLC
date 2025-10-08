import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from langfuse import Langfuse

from agents.product_owner.gatherer_agent import GathererAgent

# Load environment variables
load_dotenv()

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def print_final_summary(state_data: Dict[str, Any]) -> None:
    """In tóm tắt kết quả cuối cùng với format dễ đọc."""
    import textwrap

    print("\n" + "="*80)
    print("📊 KẾT QUẢ CUỐI CÙNG - GATHERER AGENT")
    print("="*80)

    # Brief info
    if "brief" in state_data and state_data["brief"]:
        brief = state_data["brief"]
        print(f"\n✅ PRODUCT BRIEF: {brief.get('product_name', 'N/A')}")
        print(f"   Status: {'⚠️  Chưa hoàn chỉnh' if state_data.get('incomplete_flag') else '✓ Hoàn chỉnh'}")
        print(f"   Confidence: {state_data.get('confidence', 0):.2f}")
        print(f"   Completeness: {state_data.get('score', 0):.2f}")

    # Statistics
    print(f"\n📈 THỐNG KÊ:")
    print(f"   • Số lần lặp: {state_data.get('iteration_count', 0)}/{state_data.get('max_iterations', 0)}")
    print(f"   • Số lần retry: {state_data.get('retry_count', 0)}")
    print(f"   • Tổng messages: {len(state_data.get('messages', []))}")
    print(f"   • Số gaps còn lại: {len(state_data.get('gaps', []))}")
    print(f"   • Unclear inputs: {len(state_data.get('unclear_input', []))}")

    # Brief content
    if "brief" in state_data and state_data["brief"]:
        brief = state_data["brief"]
        print(f"\n📄 NỘI DUNG BRIEF:")
        print(f"\n   🏷️  Tên sản phẩm: {brief.get('product_name', 'N/A')}")

        print(f"\n   📝 Mô tả:")
        desc = brief.get('description', 'N/A')
        for line in textwrap.wrap(desc, width=70):
            print(f"      {line}")

        print(f"\n   👥 Đối tượng mục tiêu ({len(brief.get('target_audience', []))}):")
        for i, audience in enumerate(brief.get('target_audience', []), 1):
            wrapped_lines = textwrap.wrap(audience, width=70)
            for j, line in enumerate(wrapped_lines):
                if j == 0:
                    print(f"      {i}. {line}")
                else:
                    print(f"         {line}")

        print(f"\n   ⚙️  Tính năng chính ({len(brief.get('key_features', []))}):")
        for i, feature in enumerate(brief.get('key_features', []), 1):
            wrapped_lines = textwrap.wrap(feature, width=70)
            for j, line in enumerate(wrapped_lines):
                if j == 0:
                    print(f"      {i}. {line}")
                else:
                    print(f"         {line}")

        print(f"\n   💡 Lợi ích ({len(brief.get('benefits', []))}):")
        for i, benefit in enumerate(brief.get('benefits', []), 1):
            wrapped_lines = textwrap.wrap(benefit, width=70)
            for j, line in enumerate(wrapped_lines):
                if j == 0:
                    print(f"      {i}. {line}")
                else:
                    print(f"         {line}")

        if brief.get('competitors'):
            print(f"\n   🏆 Đối thủ cạnh tranh ({len(brief.get('competitors', []))}):")
            for i, competitor in enumerate(brief.get('competitors', []), 1):
                wrapped_lines = textwrap.wrap(competitor, width=70)
                for j, line in enumerate(wrapped_lines):
                    if j == 0:
                        print(f"      {i}. {line}")
                    else:
                        print(f"         {line}")

        if brief.get('completeness_note'):
            print(f"\n   ℹ️  Ghi chú:")
            for line in textwrap.wrap(brief.get('completeness_note', ''), width=70):
                print(f"      {line}")

    # Gaps remaining
    if state_data.get('gaps'):
        print(f"\n⚠️  CÁC GAPS CÒN THIẾU ({len(state_data['gaps'])}):")
        for i, gap in enumerate(state_data['gaps'], 1):
            wrapped_lines = textwrap.wrap(gap, width=70)
            for j, line in enumerate(wrapped_lines):
                if j == 0:
                    print(f"   {i}. {line}")
                else:
                    print(f"      {line}")

    print("\n" + "="*80)
    print(f"✅ HOÀN THÀNH - Workflow status: {state_data.get('status', 'unknown')}")
    print("="*80 + "\n")


def test_gatherer_agent():
    """Test the gatherer agent with a sample product requirement."""
    print_separator()
    print("Testing Gatherer Agent")
    print_separator()

    # Generate session and user IDs for tracking
    session_id = f"test-session-{uuid.uuid4()}"
    user_id = "test-user"

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")

    # Initialize the agent with tracking IDs
    print("\nInitializing Gatherer Agent...")
    agent = GathererAgent(session_id=session_id, user_id=user_id)
    print("Agent initialized successfully")

    # Test case 1: Context ngắn, cần thu thập thêm (score < 0.8)
    initial_context = """Tôi muốn xây dựng một ứng dụng quản lý công việc thông minh sử dụng AI.

Ứng dụng này sẽ giúp người dùng quản lý task hàng ngày hiệu quả hơn.
Mục tiêu chính là tự động ưu tiên công việc dựa trên deadline và mức độ quan trọng."""

    # Test case 2: Context rất ngắn, mơ hồ (score ~ 0.1-0.2)
    initial_context_unclear = """Tôi muốn xây dựng một ứng dụng sử dụng AI như thế."""

    # Test case 3: Context đầy đủ, chi tiết (score >= 0.8)
    initial_context_complete = """Tôi muốn xây dựng một ứng dụng quản lý công việc tên là "TaskMaster Pro" sử dụng AI.

**Mô tả sản phẩm:**
TaskMaster Pro là ứng dụng quản lý công việc thông minh dành cho sinh viên và nhân viên văn phòng.
Ứng dụng sử dụng AI để tự động phân loại, ưu tiên và gợi ý thời gian hoàn thành task dựa trên lịch trình cá nhân,
deadline, và mức độ quan trọng. Điểm khác biệt là khả năng học习 thói quen làm việc của user để đưa ra đề xuất
tối ưu và tự động điều chỉnh kế hoạch khi có thay đổi.

**Đối tượng mục tiêu:**
- Sinh viên đại học: cần quản lý deadline bài tập, project nhóm, ôn thi
- Nhân viên văn phòng (25-35 tuổi): làm việc với nhiều task song song, cần tối ưu thời gian
- Freelancer: quản lý nhiều dự án khách hàng khác nhau, deadline linh hoạt

**Tính năng chính:**
1. AI Auto-Priority: Tự động sắp xếp task theo độ ưu tiên dựa trên deadline, mức độ quan trọng, và thời gian cần thiết
2. Smart Schedule: Gợi ý thời gian làm việc tối ưu dựa trên thói quen và năng suất cao nhất của user
3. Task Breakdown: Tự động chia nhỏ task lớn thành các subtask cụ thể với timeline rõ ràng
4. Focus Mode: Chế độ tập trung với Pomodoro timer, block notification và theo dõi năng suất
5. Multi-platform Sync: Đồng bộ real-time trên web, mobile (iOS/Android), và desktop

**Lợi ích:**
- Tiết kiệm 30-40% thời gian lập kế hoạch công việc nhờ AI tự động phân loại và ưu tiên
- Giảm stress do quên deadline: nhận thông báo thông minh và đề xuất điều chỉnh kế hoạch
- Tăng năng suất làm việc 25% nhờ gợi ý thời gian làm việc hiệu quả nhất
- Dễ dàng theo dõi tiến độ và phân tích năng suất qua dashboard trực quan

**Đối thủ cạnh tranh:**
- Todoist: mạnh về UI/UX nhưng thiếu tính năng AI phân tích thói quen
- Notion: đa năng nhưng phức tạp, không tối ưu cho quản lý task đơn giản
- Microsoft To Do: tích hợp tốt với Office 365 nhưng AI còn hạn chế

USP của TaskMaster Pro: AI cá nhân hóa sâu, học習 thói quen làm việc và đưa ra gợi ý proactive thay vì chỉ reminder thụ động."""

    initial_context_complete1 = """Tôi muốn xây dựng một ứng dụng quản lý công việc tên là "TaskMaster Pro" sử dụng AI.

**Mô tả sản phẩm:**
TaskMaster Pro là ứng dụng quản lý công việc thông minh dành cho sinh viên và nhân viên văn phòng.
Ứng dụng sử dụng AI để tự động phân loại, ưu tiên và gợi ý thời gian hoàn thành task dựa trên lịch trình cá nhân,
deadline, và mức độ quan trọng. Điểm khác biệt là khả năng học习 thói quen làm việc của user để đưa ra đề xuất
tối ưu và tự động điều chỉnh kế hoạch khi có thay đổi.

**Đối tượng mục tiêu:**
- Sinh viên đại học: cần quản lý deadline bài tập, project nhóm, ôn thi
- Nhân viên văn phòng (25-35 tuổi): làm việc với nhiều task song song, cần tối ưu thời gian

**Tính năng chính:**
1. AI Auto-Priority: Tự động sắp xếp task theo độ ưu tiên dựa trên deadline, mức độ quan trọng, và thời gian cần thiết
2. Smart Schedule: Gợi ý thời gian làm việc tối ưu dựa trên thói quen và năng suất cao nhất của user
3. Task Breakdown: Tự động chia nhỏ task lớn thành các subtask cụ thể với timeline rõ ràng
4. Focus Mode: Chế độ tập trung với Pomodoro timer, block notification và theo dõi năng suất
5. Multi-platform Sync: Đồng bộ real-time trên web, mobile (iOS/Android), và desktop

**Lợi ích:**
- Tiết kiệm 30-40% thời gian lập kế hoạch công việc nhờ AI tự động phân loại và ưu tiên
- Giảm stress do quên deadline: nhận thông báo thông minh và đề xuất điều chỉnh kế hoạch
- Tăng năng suất làm việc 25% nhờ gợi ý thời gian làm việc hiệu quả nhất
- Dễ dàng theo dõi tiến độ và phân tích năng suất qua dashboard trực quan

**Đối thủ cạnh tranh:**
- Todoist: mạnh về UI/UX nhưng thiếu tính năng AI phân tích thói quen
- Notion: đa năng nhưng phức tạp, không tối ưu cho quản lý task đơn giản
- Microsoft To Do: tích hợp tốt với Office 365 nhưng AI còn hạn chế

USP của TaskMaster Pro: AI cá nhân hóa sâu, học習 thói quen làm việc và đưa ra gợi ý proactive thay vì chỉ reminder thụ động."""

    print(f"\nNgữ cảnh ban đầu: {initial_context_complete}")
    print_separator()

    # Run the agent
    print("Running Gatherer Agent workflow...\n")

    try:
        result = agent.run(initial_context=initial_context_complete)

        print_separator()
        print("Workflow completed successfully!")
        print_separator()

        # Extract the final state from the result
        final_node_state = None
        if isinstance(result, dict):
            for key, value in result.items():
                final_node_state = value

        if final_node_state:
            print_final_summary(final_node_state)
        else:
            print("No final state found in result")
            print("Result:", result)

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Flush all events to Langfuse
        langfuse.flush()

    print_separator()
    return True


def main():
    """Main function."""
    print("\nProduct Owner Agent Test Suite")

    success = test_gatherer_agent()

    if success:
        print("\nAll tests completed successfully!")
        return 0
    else:
        print("\nTests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())