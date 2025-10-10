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
from agents.product_owner.vision_agent import VisionAgent
from agents.product_owner.backlog_agent import BacklogAgent

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
        print(f"   Score: {state_data.get('score', 0):.2f}")

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

    print(f"\nNgữ cảnh ban đầu: {initial_context_unclear}")
    print_separator()

    # Run the agent
    print("Running Gatherer Agent workflow...\n")

    try:
        result = agent.run(initial_context=initial_context_unclear)

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


def test_vision_agent():
    """Test the vision agent with a sample product brief."""
    print_separator()
    print("Testing Vision Agent")
    print_separator()

    # Sample product brief (từ gatherer agent output)
    product_brief = {
        "product_name": "SmartTask",
        "description": "SmartTask là ứng dụng quản lý công việc và dự án tích hợp AI, giúp người dùng tối ưu hóa hiệu suất cá nhân và nhóm. Ứng dụng cung cấp các tính năng như quản lý công việc, dự án, thông báo deadline, và chatbot AI hỗ trợ ra quyết định. Điểm khác biệt của SmartTask là sử dụng AI để tự động hóa quy trình, phân tích hiệu suất và đưa ra đề xuất thông minh, kết hợp với giao diện hiện đại, thân thiện, phù hợp cho sinh viên, nhân viên văn phòng và freelancer.",
        "target_audience": [
            "Sinh viên: Cần quản lý lịch học, bài tập, dự án nhóm để tối ưu thời gian học tập.",
            "Nhân viên văn phòng: Quản lý công việc hàng ngày, dự án nhóm, giảm áp lực deadline.",
            "Freelancer: Theo dõi nhiều dự án, khách hàng cùng lúc, cần hỗ trợ ra quyết định và nhắc nhở thông minh."
        ],
        "key_features": [
            "Quản lý công việc: Tạo, sắp xếp, theo dõi tiến độ các nhiệm vụ cá nhân hoặc nhóm.",
            "Quản lý dự án: Lập kế hoạch, phân chia công việc, theo dõi tiến độ dự án.",
            "Thông báo deadline: Nhắc nhở thông minh về các mốc thời gian quan trọng, giúp không bỏ lỡ công việc.",
            "Chatbot hỗ trợ: Chatbot AI tư vấn, trả lời câu hỏi, đề xuất giải pháp tối ưu cho công việc.",
            "[Suy luận] Phân tích hiệu suất: AI đánh giá hiệu quả làm việc, đề xuất cải tiến dựa trên dữ liệu sử dụng."
        ],
        "benefits": [
            "Tiết kiệm thời gian nhờ tự động hóa các tác vụ quản lý công việc và dự án.",
            "Tăng hiệu suất làm việc thông qua nhắc nhở deadline và phân tích hiệu suất cá nhân.",
            "Hỗ trợ ra quyết định nhanh chóng với chatbot AI tư vấn và đề xuất giải pháp.",
            "Giảm căng thẳng quản lý nhờ giao diện trực quan, hiện đại, dễ sử dụng."
        ],
        "competitors": [
            "Trello: Nền tảng quản lý dự án phổ biến với giao diện Kanban, mạnh về cộng tác nhóm nhưng chưa tích hợp sâu AI. SmartTask nổi bật nhờ tính năng AI hỗ trợ ra quyết định và giao diện hiện đại."
        ],
        "completeness_note": "Brief đã tổng hợp đầy đủ các phần chính dựa trên thông tin cung cấp. Một số chi tiết về công nghệ AI sử dụng và điểm khác biệt sâu hơn với đối thủ được suy luận hợp lý dựa trên ngữ cảnh. Nếu cần bổ sung chi tiết về workflow, AI engine hoặc trải nghiệm người dùng, cần thêm thông tin từ stakeholder."
    }

    # Generate session and user IDs
    session_id = f"test-vision-{uuid.uuid4()}"
    user_id = "test-user"

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")

    # Initialize vision agent
    print("\nInitializing Vision Agent...")
    agent = VisionAgent(session_id=session_id, user_id=user_id)
    print("Agent initialized successfully")

    print_separator()
    print("Running Vision Agent workflow...\n")

    try:
        result = agent.run(product_brief=product_brief)

        print_separator()
        print("Workflow completed successfully!")
        print_separator()

        # Print result
        print("\n📊 VISION AGENT RESULT:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        langfuse.flush()

    print_separator()
    return True


def test_backlog_agent():
    """Test the backlog agent with Product Vision input."""
    print_separator()
    print("Testing Backlog Agent")
    print_separator()

    # Sample product vision (theo format bạn cung cấp)
    product_vision = {
        "draft_vision_statement": "Tạo điều kiện để mọi người đạt được hiệu suất tối ưu trong công việc và dự án thông qua sự hỗ trợ thông minh và trải nghiệm người dùng vượt trội.",
        "experience_principles": [
            "Đơn giản hóa quy trình quản lý công việc.",
            "Tăng cường hiệu quả thông qua tự động hóa.",
            "Cung cấp thông tin hữu ích một cách kịp thời.",
            "Đảm bảo tính bảo mật và riêng tư của dữ liệu.",
            "Tạo cảm giác thân thiện và dễ tiếp cận cho người dùng."
        ],
        "problem_summary": "Người dùng gặp khó khăn trong việc quản lý công việc và dự án một cách hiệu quả, dẫn đến giảm năng suất và gia tăng căng thẳng. Cần một giải pháp tích hợp AI để tối ưu hóa quy trình và cung cấp hỗ trợ thông minh.",
        "audience_segments": [
            {
                "name": "Sinh viên",
                "description": "Sinh viên cần quản lý lịch học, bài tập và dự án nhóm.",
                "needs": [
                    "Quản lý thời gian hiệu quả.",
                    "Theo dõi tiến độ học tập.",
                    "Nhận nhắc nhở về deadline."
                ],
                "pain_points": [
                    "Khó khăn trong việc tổ chức công việc.",
                    "Áp lực từ deadline.",
                    "Thiếu công cụ hỗ trợ học tập thông minh."
                ]
            },
            {
                "name": "Nhân viên văn phòng",
                "description": "Nhân viên văn phòng cần quản lý công việc hàng ngày và dự án nhóm.",
                "needs": [
                    "Quản lý công việc hiệu quả.",
                    "Giảm áp lực từ deadline.",
                    "Hỗ trợ ra quyết định nhanh chóng."
                ],
                "pain_points": [
                    "Quá tải công việc.",
                    "Khó khăn trong việc theo dõi tiến độ nhóm.",
                    "Thiếu công cụ hỗ trợ thông minh."
                ]
            },
            {
                "name": "Freelancer",
                "description": "Freelancer cần theo dõi nhiều dự án và khách hàng cùng lúc.",
                "needs": [
                    "Quản lý nhiều dự án hiệu quả.",
                    "Nhận hỗ trợ ra quyết định.",
                    "Theo dõi deadline thông minh."
                ],
                "pain_points": [
                    "Khó khăn trong việc tổ chức công việc.",
                    "Thiếu sự hỗ trợ từ công cụ thông minh.",
                    "Áp lực từ khách hàng và deadline."
                ]
            }
        ],
        "scope_capabilities": [
            "Tự động hóa quy trình quản lý công việc.",
            "Phân tích hiệu suất làm việc của người dùng.",
            "Hỗ trợ ra quyết định thông qua AI.",
            "Cung cấp giao diện thân thiện và hiện đại."
        ],
        "scope_non_goals": [
            "Không hỗ trợ tích hợp với các nền tảng quản lý công việc khác trong phiên bản đầu tiên.",
            "Không cung cấp tính năng phân tích chuyên sâu cho các dự án lớn.",
            "Không hỗ trợ đa ngôn ngữ ngoài tiếng Anh trong phiên bản đầu tiên."
        ],
        "functional_requirements": [
            {
                "name": "Quản lý công việc",
                "description": "Cho phép người dùng tạo, sắp xếp và theo dõi tiến độ các nhiệm vụ cá nhân hoặc nhóm.",
                "priority": "High",
                "user_stories": [
                    "As a student, I want to create tasks for my assignments, so that I can manage my deadlines.",
                    "As an office worker, I want to organize my daily tasks, so that I can improve my productivity.",
                    "As a freelancer, I want to track tasks for different projects, so that I can meet client expectations."
                ],
                "acceptance_criteria": [
                    "Người dùng có thể tạo nhiệm vụ với tiêu đề, mô tả và ngày hoàn thành.",
                    "Nhiệm vụ được lưu và đồng bộ hóa trong vòng 2 giây.",
                    "Hiển thị thông báo lỗi nếu tiêu đề nhiệm vụ bị bỏ trống."
                ]
            },
            {
                "name": "Quản lý dự án",
                "description": "Cho phép người dùng lập kế hoạch, phân chia công việc và theo dõi tiến độ dự án.",
                "priority": "High",
                "user_stories": [
                    "As a student, I want to create group projects, so that I can coordinate with my teammates.",
                    "As an office worker, I want to manage team projects, so that I can ensure deadlines are met.",
                    "As a freelancer, I want to organize projects for different clients, so that I can deliver quality work."
                ],
                "acceptance_criteria": [
                    "Người dùng có thể tạo dự án với các nhiệm vụ con.",
                    "Dự án có thể được chia sẻ với các thành viên nhóm.",
                    "Hiển thị tiến độ tổng quan của dự án."
                ]
            }
        ],
        "performance_requirements": [
            "Thời gian phản hồi của hệ thống dưới 2 giây cho các thao tác cơ bản.",
            "Hệ thống hỗ trợ tối đa 10,000 người dùng đồng thời."
        ],
        "security_requirements": [
            "Dữ liệu người dùng được mã hóa cả khi truyền tải và lưu trữ.",
            "Xác thực hai yếu tố cho tài khoản người dùng.",
            "Hệ thống tuân thủ các tiêu chuẩn bảo mật quốc tế."
        ],
        "ux_requirements": [
            "Giao diện trực quan, dễ sử dụng.",
            "Hỗ trợ trên cả nền tảng web và di động.",
            "Tối ưu hóa cho trải nghiệm người dùng mới."
        ],
        "dependencies": [
            "Dịch vụ AI để phân tích hiệu suất.",
            "Hệ thống lưu trữ dữ liệu đám mây.",
            "API để tích hợp với các công cụ lịch hiện có."
        ],
        "risks": [
            "Khả năng tích hợp AI không đạt kỳ vọng.",
            "Cạnh tranh mạnh từ các sản phẩm đã có trên thị trường.",
            "Rủi ro bảo mật dữ liệu người dùng."
        ],
        "assumptions": [
            "Người dùng có kết nối internet ổn định.",
            "Người dùng có kiến thức cơ bản về sử dụng ứng dụng quản lý công việc.",
            "Dịch vụ AI sẽ hoạt động ổn định và chính xác."
        ],
        "product_name": "SmartWork"
    }

    # Generate session and user IDs
    session_id = f"test-backlog-{uuid.uuid4()}"
    user_id = "test-user"

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    print(f"Product Name: {product_vision.get('product_name')}")

    # Initialize backlog agent
    print("\nInitializing Backlog Agent...")
    agent = BacklogAgent(session_id=session_id, user_id=user_id)
    print("Agent initialized successfully")

    print_separator()
    print("Running Backlog Agent workflow...\n")

    try:
        result = agent.run(product_vision=product_vision)

        print_separator()
        print("Workflow completed successfully!")
        print_separator()

        # Print result
        print("\n📊 BACKLOG AGENT RESULT:")

        # Extract final state
        final_state = None
        if isinstance(result, dict):
            for key, value in result.items():
                final_state = value

        if final_state:
            print(f"\n✅ STATUS: {final_state.get('status', 'unknown')}")
            print(f"   Loops: {final_state.get('current_loop', 0)}/{final_state.get('max_loops', 0)}")
            print(f"   Readiness Score: {final_state.get('readiness_score', 0):.2f}")

            # Print backlog items count
            if final_state.get('backlog_items'):
                items = final_state['backlog_items']
                epics = [i for i in items if i.get('type') == 'Epic']
                stories = [i for i in items if i.get('type') == 'User Story']
                tasks = [i for i in items if i.get('type') == 'Task']
                subtasks = [i for i in items if i.get('type') == 'Sub-task']

                print(f"\n📋 BACKLOG ITEMS:")
                print(f"   - Epics: {len(epics)}")
                print(f"   - User Stories: {len(stories)}")
                print(f"   - Tasks: {len(tasks)}")
                print(f"   - Sub-tasks: {len(subtasks)}")
                print(f"   Total: {len(items)}")

            # Print product backlog if finalized
            if final_state.get('product_backlog'):
                print("\n✅ PRODUCT BACKLOG FINALIZED:")
                backlog = final_state['product_backlog']
                print(json.dumps(backlog, ensure_ascii=False, indent=2))

            print(f"\n📝 Full Result:")
            print(json.dumps(final_state, ensure_ascii=False, indent=2, default=str))
        else:
            print("No final state found in result")
            print("Result:", result)

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        langfuse.flush()

    print_separator()
    return True


def main():
    """Main function."""
    print("\nProduct Owner Agent Test Suite")

    # Test backlog agent
    success = test_backlog_agent()

    if success:
        print("\nAll tests completed successfully!")
        return 0
    else:
        print("\nTests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())