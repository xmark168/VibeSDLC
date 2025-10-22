import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from langfuse import Langfuse

from app.agents.product_owner.gatherer_agent import GathererAgent
from app.agents.product_owner.vision_agent import VisionAgent
from app.agents.product_owner.backlog_agent import BacklogAgent
from app.agents.product_owner.priority_agent import PriorityAgent
from app.agents.product_owner.po_agent import POAgent

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
deadline, và mức độ quan trọng. Điểm khác biệt là khả năng học thói quen làm việc của user để đưa ra đề xuất
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
deadline, và mức độ quan trọng. Điểm khác biệt là khả năng học thói quen làm việc của user để đưa ra đề xuất
tối ưu và tự động điều chỉnh kế hoạch khi có thay đổi. Được thiết kế trên web

**Đối tượng mục tiêu:**
- Sinh viên đại học: cần quản lý deadline bài tập, project nhóm, ôn thi
- Nhân viên văn phòng (25-35 tuổi): làm việc với nhiều task song song, cần tối ưu thời gian

**Tính năng chính:**
1. AI Auto-Priority: Tự động sắp xếp task theo độ ưu tiên dựa trên deadline, mức độ quan trọng, và thời gian cần thiết
2. Smart Schedule: Gợi ý thời gian làm việc tối ưu dựa trên thói quen và năng suất cao nhất của user
3. Task Breakdown: Tự động chia nhỏ task lớn thành các subtask cụ thể với timeline rõ ràng
4. Focus Mode: Chế độ tập trung với Pomodoro timer, block notification và theo dõi năng suất

**Lợi ích:**
- Tiết kiệm 30-40% thời gian lập kế hoạch công việc nhờ AI tự động phân loại và ưu tiên
- Giảm stress do quên deadline: nhận thông báo thông minh và đề xuất điều chỉnh kế hoạch
- Tăng năng suất làm việc 25% nhờ gợi ý thời gian làm việc hiệu quả nhất
- Dễ dàng theo dõi tiến độ và phân tích năng suất qua dashboard trực quan

**Đối thủ cạnh tranh:**
- Todoist: mạnh về UI/UX nhưng thiếu tính năng AI phân tích thói quen
- Notion: đa năng nhưng phức tạp, không tối ưu cho quản lý task đơn giản

USP của TaskMaster Pro: AI cá nhân hóa sâu, học thói quen làm việc và đưa ra gợi ý proactive thay vì chỉ reminder thụ động."""

    print(f"\nNgữ cảnh ban đầu: {initial_context_complete1}")
    print_separator()

    # Run the agent
    print("Running Gatherer Agent workflow...\n")

    try:
        result = agent.run(initial_context=initial_context_complete1)

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
            print("\nResult:")
            print(json.dumps(result, ensure_ascii=False, indent=2))

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

                print(f"\n📋 BACKLOG ITEMS:")
                print(f"   - Epics: {len(epics)}")
                print(f"   - User Stories: {len(stories)}")
                print(f"   - Tasks: {len(tasks)}")
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
            print("\nResult:")
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


def test_priority_agent():
    """Test the priority agent with Product Backlog input."""
    print_separator()
    print("Testing Priority Agent")
    print_separator()

    # Sample product backlog (compact version from your data)
    product_backlog = {
        "metadata": {
            "product_name": "SmartWork",
            "version": "v1.0",
            "total_items": 37,
            "total_epics": 5,
            "total_user_stories": 26,
            "total_tasks": 2,
            "total_subtasks": 4,
            "total_story_points": 92,
            "total_estimate_hours": 26.0
        },
        "items": [
            # Epic 1
            {
                "id": "EPIC-001",
                "type": "Epic",
                "parent_id": None,
                "title": "AI Auto-Priority & Smart Scheduling",
                "description": "Build the core AI engine to automatically prioritize, schedule, and suggest optimal times for task completion based on user habits, deadlines, and importance.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": None,
                "acceptance_criteria": [],
                "dependencies": [],
                "labels": ["core", "ai", "scheduling"],
                "task_type": None,
                "business_value": "Delivers the main value proposition of TaskMaster Pro by saving users time and boosting productivity through intelligent automation."
            },
            {
                "id": "EPIC-002",
                "type": "Epic",
                "parent_id": None,
                "title": "Task Management & Breakdown",
                "description": "Enable users to create, edit, delete, and organize tasks, including automatic breakdown of large tasks into actionable subtasks with clear timelines.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": None,
                "acceptance_criteria": [],
                "dependencies": [],
                "labels": ["core", "task-management"],
                "task_type": None,
                "business_value": "Empowers users to manage their workload efficiently and avoid missing deadlines by structuring tasks clearly."
            },
            {
                "id": "EPIC-003",
                "type": "Epic",
                "parent_id": None,
                "title": "Focus Mode & Productivity Tracking",
                "description": "Provide users with a distraction-free focus mode (Pomodoro, notification blocking) and real-time productivity tracking to enhance concentration and self-awareness.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": None,
                "acceptance_criteria": [],
                "dependencies": [],
                "labels": ["productivity", "focus"],
                "task_type": None,
                "business_value": "Helps users stay focused, reduce stress, and improve work efficiency through guided work sessions."
            },
            {
                "id": "EPIC-004",
                "type": "Epic",
                "parent_id": None,
                "title": "Multi-Platform Real-Time Sync",
                "description": "Implement seamless real-time data synchronization across web, mobile, and desktop platforms so users can access up-to-date information anywhere.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": None,
                "acceptance_criteria": [],
                "dependencies": [],
                "labels": ["sync", "multi-platform"],
                "task_type": None,
                "business_value": "Ensures users always have access to their latest tasks and schedules, regardless of device."
            },
            {
                "id": "EPIC-005",
                "type": "Epic",
                "parent_id": None,
                "title": "User Authentication & Security",
                "description": "Provide secure user authentication, data encryption, and access control to protect user information and ensure privacy.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": None,
                "acceptance_criteria": [],
                "dependencies": [],
                "labels": ["security", "authentication"],
                "task_type": None,
                "business_value": "Builds user trust and meets compliance requirements by safeguarding sensitive data."
            },
            # User Stories for Epic 1
            {
                "id": "US-001",
                "type": "User Story",
                "parent_id": "EPIC-001",
                "title": "As a student, I want the system to prioritize my tasks so that I can focus on the most urgent ones",
                "description": "Automatically prioritize tasks for students based on deadlines and importance to help them avoid missing critical assignments.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given a list of tasks with deadlines, When the user views their task list, Then tasks are ordered by urgency and importance",
                    "Given a new task is added, When it has a closer deadline than others, Then it appears higher in the list",
                    "Given user marks a task as important, When viewing the list, Then the important task is prioritized accordingly",
                    "Given multiple tasks have the same priority or deadline, When viewing the list, Then tasks are sorted by creation time or user preference",
                    "Given user overrides AI prioritization, When viewing the list, Then the user-defined order is respected"
                ],
                "dependencies": [],
                "labels": ["ai", "scheduling", "student"],
                "task_type": None,
                "business_value": "Helps students avoid missing deadlines and focus on high-priority work."
            },
            {
                "id": "US-009",
                "type": "User Story",
                "parent_id": "EPIC-001",
                "title": "As a student, I want to manually override AI prioritization so that I can adjust my task order",
                "description": "Allow users to manually reorder tasks and override AI suggestions for prioritization.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user wants to change task order, When user drags and drops a task, Then the new order is saved and reflected in the list",
                    "Given user overrides AI, When viewing the list, Then AI suggestions are not applied to overridden tasks",
                    "Given user resets overrides, When confirmed, Then AI prioritization is restored"
                ],
                "dependencies": [],
                "labels": ["ai", "scheduling", "student"],
                "task_type": None,
                "business_value": "Gives users control over their workflow and increases trust in the system."
            },
            {
                "id": "US-002",
                "type": "User Story",
                "parent_id": "EPIC-001",
                "title": "As an office worker, I want suggestions for optimal working times so that I can maximize my productivity",
                "description": "AI analyzes user work habits and suggests the best times to complete tasks for peak productivity.",
                "rank": None,
                "status": "Backlog",
                "story_point": 5,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user has a history of task completions, When viewing task suggestions, Then system recommends time slots based on past productivity",
                    "Given user accepts a suggested time, When the time arrives, Then a notification is sent to start the task",
                    "Given user ignores a suggestion, When rescheduling, Then AI adapts future suggestions accordingly",
                    "Given user has no activity history, When viewing suggestions, Then system prompts user to manually set preferred times or uses default recommendations",
                    "Given user repeatedly rejects all suggestions, When viewing future suggestions, Then AI reduces frequency or asks for feedback"
                ],
                "dependencies": [],
                "labels": ["ai", "scheduling", "office-worker"],
                "task_type": None,
                "business_value": "Boosts productivity by aligning work with user’s natural high-performance periods."
            },
            {
                "id": "US-003",
                "type": "User Story",
                "parent_id": "EPIC-002",
                "title": "As a user, I want to create and organize tasks so that I can manage my workload efficiently",
                "description": "Allow users to add, edit, delete, and organize tasks into lists or categories for better management.",
                "rank": None,
                "status": "Backlog",
                "story_point": 5,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user is on the dashboard, When user creates a new task, Then the task appears in the selected list or category",
                    "Given user edits a task, When changes are saved, Then the updated task details are displayed",
                    "Given user deletes a task, When confirmed, Then the task is removed from the list",
                    "Given user tries to create a task with missing required fields, When submitting, Then an error message is shown",
                    "Given user organizes tasks, When moving a task to a different list or category, Then the change is reflected in the UI",
                    "Given server error occurs during task creation, When user submits, Then user is notified and can retry"
                ],
                "dependencies": ["US-001", "US-002"],
                "labels": ["ai", "reminder"],
                "task_type": None,
                "business_value": "Enables users to keep track of all their responsibilities in one place."
            },
            {
                "id": "US-004",
                "type": "User Story",
                "parent_id": "EPIC-002",
                "title": "As a user, I want large tasks to be automatically broken down into subtasks so that I can tackle them step by step",
                "description": "AI analyzes large tasks and generates a sequence of actionable subtasks with deadlines.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user creates a large task, When AI detects complexity, Then subtasks are generated automatically",
                    "Given subtasks are created, When user views the task, Then subtasks are displayed with individual deadlines",
                    "Given user completes a subtask, When progress is updated, Then parent task progress reflects the change",
                    "Given AI cannot analyze the task, When breakdown fails, Then user is notified of the failure"
                ],
                "dependencies": ["US-003"],
                "labels": ["ai", "task-management"],
                "task_type": None,
                "business_value": "Reduces overwhelm and increases completion rates for complex projects."
            },
            {
                "id": "US-012",
                "type": "User Story",
                "parent_id": "EPIC-002",
                "title": "As a user, I want to be notified and manually create/edit subtasks if AI breakdown fails so that I can still organize my work",
                "description": "If AI breakdown fails, notify user and allow manual subtask creation and editing.",
                "rank": None,
                "status": "Backlog",
                "story_point": 2,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given AI fails to generate subtasks, When user is notified, Then user can manually create subtasks",
                    "Given user creates or edits subtasks manually, When saved, Then changes are reflected in the parent task",
                    "Given user ignores notification, When returning later, Then manual subtask creation is still available"
                ],
                "dependencies": ["US-004"],
                "labels": ["task-management", "notification"],
                "task_type": None,
                "business_value": "Ensures users can organize their work even when AI fails, improving reliability."
            },
            {
                "id": "US-010",
                "type": "User Story",
                "parent_id": "EPIC-002",
                "title": "As a user, I want to manually edit subtasks generated by AI so that I can customize my workflow",
                "description": "Allow users to modify, delete, or add subtasks after AI breakdown.",
                "rank": None,
                "status": "Backlog",
                "story_point": 2,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given subtasks are generated by AI, When user edits a subtask, Then changes are saved and reflected in the parent task",
                    "Given user deletes a subtask, When confirmed, Then subtask is removed and progress is updated",
                    "Given user adds a new subtask, When saved, Then it appears in the list with a deadline"
                ],
                "dependencies": ["US-004"],
                "labels": ["task-management", "ai"],
                "task_type": None,
                "business_value": "Allows users to personalize their workflow and increases flexibility."
            },
            {
                "id": "US-005",
                "type": "User Story",
                "parent_id": "EPIC-003",
                "title": "As a user, I want to activate focus mode so that I can work without distractions",
                "description": "Enable a focus mode with Pomodoro timer and notification blocking to help users concentrate.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user starts focus mode, When timer is running, Then notifications are blocked",
                    "Given focus session ends, When timer completes, Then user receives a break notification",
                    "Given user pauses focus mode, When resumed, Then timer continues from where it left off"
                ],
                "dependencies": ["US-004"],
                "labels": ["focus", "productivity"],
                "task_type": None,
                "business_value": "Improves user concentration and helps maintain work-life balance."
            },
            {
                "id": "US-006",
                "type": "User Story",
                "parent_id": "EPIC-003",
                "title": "As a user, I want to see my productivity stats so that I can track my progress over time",
                "description": "Display a dashboard with productivity analytics such as completed tasks and focus sessions.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user accesses dashboard, When data is loaded, Then completed tasks and focus sessions are displayed visually as bar charts",
                    "Given user completes tasks, When dashboard is refreshed, Then stats update in real-time",
                    "Given data fails to load, When accessing dashboard, Then user is notified and can retry",
                    "Given user views dashboard, When selecting a time range, Then data is filtered accordingly"
                ],
                "dependencies": [],
                "labels": ["productivity", "dashboard"],
                "task_type": None,
                "business_value": "Motivates users to improve by providing actionable insights."
            },
            {
                "id": "US-013",
                "type": "User Story",
                "parent_id": "EPIC-003",
                "title": "As a user, I want to view productivity trends so that I can analyze my long-term progress",
                "description": "Show productivity trends with charts and analytics, including error handling and data refresh logic.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user views trends, When selecting a time range, Then line charts display productivity over time",
                    "Given data fails to refresh, When user requests update, Then user is notified and can retry",
                    "Given user selects chart type, When switching between bar and line charts, Then data is displayed accordingly",
                    "Given server error occurs, When loading trends, Then user receives error message"
                ],
                "dependencies": ["US-006"],
                "labels": ["dashboard", "analytics"],
                "task_type": None,
                "business_value": "Helps users understand and improve productivity patterns."
            },
            {
                "id": "US-007",
                "type": "User Story",
                "parent_id": "EPIC-003",
                "title": "As a user, I want my tasks to sync in real-time across all devices so that I always have up-to-date information",
                "description": "Implement real-time synchronization for tasks and schedules between web, mobile, and desktop.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user updates a task on one device, When another device is online, Then the update appears instantly",
                    "Given user is offline, When reconnecting, Then changes are synced automatically",
                    "Given a conflict occurs, When syncing, Then user is prompted to resolve the conflict",
                    "Given sync fails partially, When retry is attempted, Then user is notified of which items failed and can retry",
                    "Given sync latency occurs, When syncing, Then user sees a loading indicator until sync completes",
                    "Given user is offline for an extended period, When reconnecting, Then system merges changes and prompts for conflict resolution if needed"
                ],
                "dependencies": [],
                "labels": ["sync", "multi-platform"],
                "task_type": None,
                "business_value": "Ensures seamless workflow regardless of device or location."
            },
            {
                "id": "US-011",
                "type": "User Story",
                "parent_id": "EPIC-004",
                "title": "As a user, I want the system to handle sync failures gracefully so that my data is not lost",
                "description": "Provide robust error handling and user feedback for sync failures and long offline periods.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given sync fails, When user is notified, Then user can retry or view offline data",
                    "Given data conflict is complex, When syncing, Then system provides detailed options for resolution",
                    "Given user is offline for a long time, When reconnecting, Then system ensures all changes are merged and no data is lost",
                    "Given sync fails partially, When retry is attempted, Then user is notified of which items failed and can retry",
                    "Given sync latency occurs, When syncing, Then user sees a loading indicator until sync completes",
                    "Given user is offline for an extended period, When reconnecting, Then system merges changes and prompts for conflict resolution if needed"
                ],
                "dependencies": ["US-007"],
                "labels": ["sync", "error-handling"],
                "task_type": None,
                "business_value": "Protects user data integrity and improves trust in multi-platform sync."
            },
            {
                "id": "US-008",
                "type": "User Story",
                "parent_id": "EPIC-005",
                "title": "As a user, I want to register and login securely so that my data is protected",
                "description": "Provide secure registration and login with encrypted credentials and session management.",
                "rank": None,
                "status": "Backlog",
                "story_point": 3,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Given user registers with email and password, When credentials are valid, Then account is created securely",
                    "Given user logs in, When credentials are correct, Then user is authenticated and session is started",
                    "Given user logs out, When action is confirmed, Then session is terminated and access is revoked",
                    "Given sync fails partially, When retry is attempted, Then user is notified of which items failed and can retry",
                    "Given sync latency occurs, When syncing, Then user sees a loading indicator until sync completes",
                    "Given user is offline for an extended period, When reconnecting, Then system merges changes and prompts for conflict resolution if needed"
                ],
                "dependencies": [],
                "labels": ["authentication", "security"],
                "task_type": None,
                "business_value": "Protects user data and builds trust in the application."
            },
            {
                "id": "TASK-001",
                "type": "Task",
                "parent_id": "EPIC-005",
                "title": "Implement data encryption for user information",
                "description": "Apply encryption for user data at rest and in transit using industry standards.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": None,
                "acceptance_criteria": [
                    "All sensitive user data is encrypted at rest",
                    "Data transmitted between client and server uses HTTPS/TLS",
                    "Encryption keys are securely managed"
                ],
                "dependencies": [],
                "labels": ["infrastructure", "security"],
                "task_type": "Infrastructure",
                "business_value": None
            },
            {
                "id": "TASK-002",
                "type": "Task",
                "parent_id": "EPIC-004",
                "title": "Setup cloud storage and sync API",
                "description": "Configure cloud storage and develop API endpoints for real-time data synchronization.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": None,
                "acceptance_criteria": [
                    "Cloud storage is provisioned and accessible",
                    "Sync API endpoints are available for CRUD operations",
                    "API supports real-time updates via websockets or similar"
                ],
                "dependencies": [],
                "labels": ["infrastructure", "sync"],
                "task_type": "Infrastructure",
                "business_value": None
            },
            {
                "id": "SUB-001",
                "type": "Sub-task",
                "parent_id": "US-001",
                "title": "Develop AI task prioritization algorithm",
                "description": "Implement algorithm to rank tasks by urgency and importance.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 8,
                "acceptance_criteria": [
                    "Algorithm calculates priority score for each task",
                    "Tasks are sorted by score in UI",
                    "Priority adapts as deadlines or importance change"
                ],
                "dependencies": [],
                "labels": ["ai", "backend"],
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-002",
                "type": "Sub-task",
                "parent_id": "US-002",
                "title": "Implement AI-based time suggestion module",
                "description": "Build module to analyze user activity and suggest optimal work times.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 10,
                "acceptance_criteria": [
                    "Module analyzes user task completion history",
                    "Suggests time slots for new tasks",
                    "Learns and adapts suggestions over time"
                ],
                "dependencies": [],
                "labels": ["ai", "backend"],
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-003",
                "type": "Sub-task",
                "parent_id": "US-003",
                "title": "Create task CRUD API endpoints",
                "description": "Develop backend endpoints for creating, updating, deleting, and listing tasks.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 8,
                "acceptance_criteria": [
                    "POST /tasks creates a new task",
                    "GET /tasks returns all tasks for user",
                    "PUT /tasks/:id updates task details",
                    "DELETE /tasks/:id removes task"
                ],
                "dependencies": [],
                "labels": ["ai", "backend"],
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-004",
                "type": "Sub-task",
                "parent_id": "US-004",
                "title": "Develop AI subtask generation logic",
                "description": "Implement logic to break down large tasks into subtasks with deadlines.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 6,
                "acceptance_criteria": [
                    "AI detects large/complex tasks",
                    "Subtasks are generated with clear descriptions",
                    "Each subtask has an assigned deadline" 
                ],
                "dependencies": [],
                "labels": ["ai", "backend"],
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-005",
                "type": "Sub-task",
                "parent_id": "US-005",
                "title": "Build focus mode UI with Pomodoro timer",
                "description": "Create UI component for focus mode and Pomodoro timer controls.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 6,
                "acceptance_criteria": [
                    "UI displays timer and session controls",
                    "Notifications are blocked during session",
                    "Break alerts are shown after session ends"
                ],
                "dependencies": [],
                "labels": ["frontend", "focus"],
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-006",
                "type": "Sub-task",
                "parent_id": "US-006",
                "title": "Implement productivity dashboard UI",
                "description": "Develop dashboard to visualize productivity stats and trends.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 8,
                "acceptance_criteria": [
                    "Dashboard displays completed tasks and focus sessions",
                    "Trends are shown with charts/graphs",
                    "Data updates in real-time"
                ],
                "dependencies": [],
                "labels": ["frontend", "dashboard"],
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-007",
                "type": "Sub-task",
                "parent_id": "US-007",
                "title": "Integrate real-time sync with cloud API",
                "description": "Connect frontend to cloud sync API for instant updates.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 10,
                "acceptance_criteria": [
                    "Frontend receives updates via websockets",
                    "Changes are reflected instantly across devices",
                    "Handles offline/online transitions gracefully"
                ],
                "dependencies": ["TASK-002"],
                "labels": ["frontend", "sync"]  ,
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-008",
                "type": "Sub-task",
                "parent_id": "US-008",
                "title": "Develop registration and login API",
                "description": "Create secure API endpoints for user registration and login.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 8,
                "acceptance_criteria": [
                    "POST /auth/register creates new user with encrypted password",
                    "POST /auth/login authenticates user and returns session token",
                    "Sessions expire after configurable period"
                ],
                "dependencies": [],
                "labels": ["backend", "authentication"],
                "task_type": "Development",
                "business_value": None
            },
            {
                "id": "SUB-009",
                "type": "Sub-task",
                "parent_id": "TASK-001",
                "title": "Configure encryption for user data at rest",
                "description": "Apply encryption to database fields storing sensitive user info.",
                "rank": None,
                "status": "Backlog",
                "story_point": None,
                "estimate_value": 8,
                "acceptance_criteria": [
                    "Sensitive fields are encrypted in database",
                    "Encryption keys are stored securely",
                    "Data is decrypted only for authenticated sessions"
                ],
                "dependencies": [],
                "labels": ["backend", "security"],
                "task_type": "Development",
                "business_value": None
            },
        ]
    }

    # Generate session and user IDs
    session_id = f"test-priority-{uuid.uuid4()}"
    user_id = "test-user"

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    print(f"Product Name: {product_backlog['metadata'].get('product_name')}")
    print(f"Total Items: {product_backlog['metadata'].get('total_items')}")

    # Initialize priority agent
    print("\nInitializing Priority Agent...")
    agent = PriorityAgent(session_id=session_id, user_id=user_id)
    print("Agent initialized successfully")

    print_separator()
    print("Running Priority Agent workflow...\n")

    try:
        result = agent.run(product_backlog=product_backlog)

        print_separator()
        print("Workflow completed successfully!")
        print_separator()

        # Print result
        print("\n📊 PRIORITY AGENT RESULT:")

        # Extract final state
        final_state = None
        if isinstance(result, dict):
            for key, value in result.items():
                final_state = value

        if final_state:
            print(f"\n✅ STATUS: {final_state.get('status', 'unknown')}")
            print(f"   Loops: {final_state.get('current_loop', 0)}/{final_state.get('max_loops', 0)}")
            print(f"   Readiness Score: {final_state.get('readiness_score', 0):.2f}")

            # Print prioritized backlog
            if final_state.get('prioritized_backlog'):
                items = final_state['prioritized_backlog']
                print(f"\n📋 PRIORITIZED BACKLOG:")
                print(f"   Total Items: {len(items)}")

                # Show top 10 prioritized items
                print(f"\n   Top 10 Prioritized Items:")
                sorted_items = sorted([i for i in items if i.get('rank')], key=lambda x: x.get('rank', 999))
                for item in sorted_items[:10]:
                    print(f"   {item.get('rank', 'N/A')}. [{item.get('type')}] {item.get('id')}: {item.get('title', '')[:60]}...")

            # Print sprints
            if final_state.get('sprints'):
                sprints = final_state['sprints']
                print(f"\n🏃 SPRINT PLAN:")
                print(f"   Total Sprints: {len(sprints)}")

                for sprint in sprints:
                    print(f"\n   Sprint {sprint.get('sprint_number')}:")
                    print(f"      Goal: {sprint.get('sprint_goal', 'N/A')}")
                    print(f"      Items: {len(sprint.get('assigned_items', []))}")
                    print(f"      Velocity Plan: {sprint.get('velocity_plan', 0)} points")
                    print(f"      Status: {sprint.get('status', 'N/A')}")

            # Print sprint plan if finalized
            if final_state.get('sprint_plan'):
                print("\n✅ SPRINT PLAN FINALIZED:")
                sprint_plan = final_state['sprint_plan']
                print(json.dumps(sprint_plan, ensure_ascii=False, indent=2))

            print(f"\n📝 Full Result:")
            print(json.dumps(final_state, ensure_ascii=False, indent=2, default=str))
        else:
            print("No final state found in result")
            print("\nResult:")
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


def test_full_po_pipeline():
    """Test toàn bộ Product Owner Agent pipeline: Gatherer → Vision → Backlog → Priority."""
    print("\n" + "="*80)
    print("🚀 TESTING FULL PRODUCT OWNER AGENT PIPELINE")
    print("="*80)
    print("\nPipeline: Gatherer Agent → Vision Agent → Backlog Agent → Priority Agent")
    print("="*80 + "\n")

    # Generate session and user IDs
    session_id = f"test-full-po-{uuid.uuid4()}"
    user_id = "test-user"

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}\n")

    # ========================================================================
    # STAGE 1: GATHERER AGENT
    # ========================================================================
    print_separator()
    print("STAGE 1: GATHERER AGENT - Thu thập Product Brief")
    print_separator()

    # Initial context - test case đầy đủ
#     initial_context = """Tôi muốn xây dựng một ứng dụng quản lý công việc tên là "TaskMaster Pro" sử dụng AI.

# **Mô tả sản phẩm:**
# TaskMaster Pro là ứng dụng quản lý công việc thông minh dành cho sinh viên và nhân viên văn phòng.
# Ứng dụng sử dụng AI để tự động phân loại, ưu tiên và gợi ý thời gian hoàn thành task dựa trên lịch trình cá nhân,
# deadline, và mức độ quan trọng. Điểm khác biệt là khả năng học thói quen làm việc của user để đưa ra đề xuất
# tối ưu và tự động điều chỉnh kế hoạch khi có thay đổi.

# **Đối tượng mục tiêu:**
# - Sinh viên đại học: cần quản lý deadline bài tập, project nhóm, ôn thi
# - Nhân viên văn phòng (25-35 tuổi): làm việc với nhiều task song song, cần tối ưu thời gian

# **Tính năng chính:**
# 1. AI Auto-Priority: Tự động sắp xếp task theo độ ưu tiên dựa trên deadline, mức độ quan trọng, và thời gian cần thiết
# 2. Smart Schedule: Gợi ý thời gian làm việc tối ưu dựa trên thói quen và năng suất cao nhất của user
# 3. Task Breakdown: Tự động chia nhỏ task lớn thành các subtask cụ thể với timeline rõ ràng
# 4. Focus Mode: Chế độ tập trung với Pomodoro timer, block notification và theo dõi năng suất
# 5. Multi-platform Sync: Đồng bộ real-time trên web, mobile (iOS/Android), và desktop

# **Lợi ích:**
# - Tiết kiệm 30-40% thời gian lập kế hoạch công việc nhờ AI tự động phân loại và ưu tiên
# - Giảm stress do quên deadline: nhận thông báo thông minh và đề xuất điều chỉnh kế hoạch
# - Tăng năng suất làm việc 25% nhờ gợi ý thời gian làm việc hiệu quả nhất
# - Dễ dàng theo dõi tiến độ và phân tích năng suất qua dashboard trực quan

# **Đối thủ cạnh tranh:**
# - Todoist: mạnh về UI/UX nhưng thiếu tính năng AI phân tích thói quen
# - Notion: đa năng nhưng phức tạp, không tối ưu cho quản lý task đơn giản
# - Microsoft To Do: tích hợp tốt với Office 365 nhưng AI còn hạn chế

# USP của TaskMaster Pro: AI cá nhân hóa sâu, học thói quen làm việc và đưa ra gợi ý proactive thay vì chỉ reminder thụ động."""

    initial_context = """Tôi muốn xây dựng một ứng dụng quản lý công việc thông minh sử dụng AI.

Ứng dụng này sẽ giúp người dùng quản lý task hàng ngày hiệu quả hơn.
Mục tiêu chính là tự động ưu tiên công việc dựa trên deadline và mức độ quan trọng."""

    print(f"Initial Context:\n{initial_context[:200]}...\n")

    try:
        # Initialize Gatherer Agent
        print("Initializing Gatherer Agent...")
        gatherer_agent = GathererAgent(session_id=session_id, user_id=user_id)
        print("✓ Gatherer Agent initialized\n")

        # Run Gatherer Agent
        print("Running Gatherer Agent...\n")
        gatherer_result = gatherer_agent.run(initial_context=initial_context)

        # Extract product brief from gatherer result
        gatherer_state = None
        if isinstance(gatherer_result, dict):
            for key, value in gatherer_result.items():
                gatherer_state = value

        if not gatherer_state or not gatherer_state.get('brief'):
            print("❌ Gatherer Agent failed to produce product brief")
            return False

        product_brief = gatherer_state['brief']
        print(f"\n✅ Gatherer Agent completed!")
        print(f"   Product: {product_brief.get('product_name', 'N/A')}")
        print(f"   Score: {gatherer_state.get('score', 0):.2f}")
        print(f"   Key Features: {len(product_brief.get('key_features', []))}")

        # ========================================================================
        # STAGE 2: VISION AGENT
        # ========================================================================
        print_separator()
        print("STAGE 2: VISION AGENT - Tạo Product Vision")
        print_separator()

        # Initialize Vision Agent
        print("Initializing Vision Agent...")
        vision_agent = VisionAgent(session_id=session_id, user_id=user_id)
        print("✓ Vision Agent initialized\n")

        # Run Vision Agent
        print("Running Vision Agent...\n")
        vision_result = vision_agent.run(product_brief=product_brief)

        # Extract product vision
        if not vision_result or not isinstance(vision_result, dict):
            print("❌ Vision Agent failed to produce product vision")
            return False

        product_vision = vision_result
        print(f"\n✅ Vision Agent completed!")
        print(f"   Product: {product_vision.get('product_name', 'N/A')}")
        print(f"   Vision Statement: {product_vision.get('draft_vision_statement', 'N/A')[:80]}...")
        print(f"   Audience Segments: {len(product_vision.get('audience_segments', []))}")
        print(f"   Functional Requirements: {len(product_vision.get('functional_requirements', []))}")

        # ========================================================================
        # STAGE 3: BACKLOG AGENT
        # ========================================================================
        print_separator()
        print("STAGE 3: BACKLOG AGENT - Tạo Product Backlog")
        print_separator()

        # Initialize Backlog Agent
        print("Initializing Backlog Agent...")
        backlog_agent = BacklogAgent(session_id=session_id, user_id=user_id)
        print("✓ Backlog Agent initialized\n")

        # Run Backlog Agent
        print("Running Backlog Agent...\n")
        backlog_result = backlog_agent.run(product_vision=product_vision)

        # Extract product backlog
        backlog_state = None
        if isinstance(backlog_result, dict):
            for key, value in backlog_result.items():
                backlog_state = value

        if not backlog_state or not backlog_state.get('product_backlog'):
            print("❌ Backlog Agent failed to produce product backlog")
            return False

        product_backlog = backlog_state['product_backlog']
        print(f"\n✅ Backlog Agent completed!")
        print(f"   Product: {product_backlog.get('metadata', {}).get('product_name', 'N/A')}")
        print(f"   Total Items: {product_backlog.get('metadata', {}).get('total_items', 0)}")
        print(f"   Epics: {product_backlog.get('metadata', {}).get('total_epics', 0)}")
        print(f"   User Stories: {product_backlog.get('metadata', {}).get('total_user_stories', 0)}")
        print(f"   Tasks: {product_backlog.get('metadata', {}).get('total_tasks', 0)}")
        print(f"   Readiness Score: {backlog_state.get('readiness_score', 0):.2f}")

        # ========================================================================
        # STAGE 4: PRIORITY AGENT
        # ========================================================================
        print_separator()
        print("STAGE 4: PRIORITY AGENT - Tạo Sprint Plan")
        print_separator()

        # Initialize Priority Agent
        print("Initializing Priority Agent...")
        priority_agent = PriorityAgent(session_id=session_id, user_id=user_id)
        print("✓ Priority Agent initialized\n")

        # Run Priority Agent
        print("Running Priority Agent...\n")
        priority_result = priority_agent.run(product_backlog=product_backlog)

        # Extract sprint plan
        if not priority_result or not isinstance(priority_result, dict):
            print("❌ Priority Agent failed to produce sprint plan")
            return False

        sprint_plan = priority_result
        print(f"\n✅ Priority Agent completed!")
        print(f"   Product: {sprint_plan.get('metadata', {}).get('product_name', 'N/A')}")
        print(f"   Total Sprints: {sprint_plan.get('metadata', {}).get('total_sprints', 0)}")
        print(f"   Total Items Assigned: {sprint_plan.get('metadata', {}).get('total_items_assigned', 0)}")
        print(f"   Total Story Points: {sprint_plan.get('metadata', {}).get('total_story_points', 0)}")
        print(f"   Readiness Score: {sprint_plan.get('metadata', {}).get('readiness_score', 0):.2f}")

        # ========================================================================
        # FINAL SUMMARY
        # ========================================================================
        print_separator()
        print("🎉 FULL PIPELINE COMPLETED SUCCESSFULLY!")
        print_separator()

        print("\n📊 PIPELINE SUMMARY:")
        print(f"\n   1️⃣  Gatherer Agent:")
        print(f"      ✓ Product Brief: {product_brief.get('product_name', 'N/A')}")
        print(f"      ✓ Score: {gatherer_state.get('score', 0):.2f}")

        print(f"\n   2️⃣  Vision Agent:")
        print(f"      ✓ Product Vision: {product_vision.get('product_name', 'N/A')}")
        print(f"      ✓ Audience Segments: {len(product_vision.get('audience_segments', []))}")
        print(f"      ✓ Functional Requirements: {len(product_vision.get('functional_requirements', []))}")

        print(f"\n   3️⃣  Backlog Agent:")
        print(f"      ✓ Product Backlog: {product_backlog.get('metadata', {}).get('product_name', 'N/A')}")
        print(f"      ✓ Total Items: {product_backlog.get('metadata', {}).get('total_items', 0)}")
        print(f"      ✓ Epics: {product_backlog.get('metadata', {}).get('total_epics', 0)}")
        print(f"      ✓ User Stories: {product_backlog.get('metadata', {}).get('total_user_stories', 0)}")

        print(f"\n   4️⃣  Priority Agent:")
        print(f"      ✓ Sprint Plan: {sprint_plan.get('metadata', {}).get('product_name', 'N/A')}")
        print(f"      ✓ Total Sprints: {sprint_plan.get('metadata', {}).get('total_sprints', 0)}")
        print(f"      ✓ Total Items Assigned: {sprint_plan.get('metadata', {}).get('total_items_assigned', 0)}")
        print(f"      ✓ Story Points: {sprint_plan.get('metadata', {}).get('total_story_points', 0)}")

        print(f"\n🎯 FINAL OUTPUT - Sprint Plan Ready for Dev Agent!")
        print(f"   Product: {sprint_plan.get('metadata', {}).get('product_name', 'N/A')}")
        print(f"   Status: {sprint_plan.get('metadata', {}).get('status', 'N/A')}")
        print(f"   Created: {sprint_plan.get('metadata', {}).get('created_at', 'N/A')}")

        print("\n" + "="*80)
        print("✅ ALL STAGES COMPLETED SUCCESSFULLY!")
        print("="*80 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Flush all events to Langfuse
        langfuse.flush()


def test_po_agent():
    """Test PO Agent (Deep Agent với tool-calling orchestration)."""
    print_separator()
    print("Testing PO Agent (Deep Agent Pattern)")
    print_separator()

    # Generate session and user IDs
    session_id = f"test-po-agent-{uuid.uuid4()}"
    user_id = "test-user"

    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}\n")

    user_input = """Tôi muốn xây dựng một ứng dụng quản lý công việc tên là "TaskMaster Pro" sử dụng AI.

    **Mô tả sản phẩm:**
    TaskMaster Pro là ứng dụng quản lý công việc thông minh dành cho sinh viên và nhân viên văn phòng.
    Ứng dụng sử dụng AI để tự động phân loại, ưu tiên và gợi ý thời gian hoàn thành task dựa trên lịch trình cá nhân,
    deadline, và mức độ quan trọng. Điểm khác biệt là khả năng học thói quen làm việc của user để đưa ra đề xuất
    tối ưu và tự động điều chỉnh kế hoạch khi có thay đổi. Được thiết kế trên web

    **Đối tượng mục tiêu:**
    - Sinh viên đại học: cần quản lý deadline bài tập, project nhóm, ôn thi
    - Nhân viên văn phòng (25-35 tuổi): làm việc với nhiều task song song, cần tối ưu thời gian

    **Tính năng chính:**
    1. AI Auto-Priority: Tự động sắp xếp task theo độ ưu tiên dựa trên deadline, mức độ quan trọng, và thời gian cần thiết
    2. Smart Schedule: Gợi ý thời gian làm việc tối ưu dựa trên thói quen và năng suất cao nhất của user
    3. Task Breakdown: Tự động chia nhỏ task lớn thành các subtask cụ thể với timeline rõ ràng
    4. Focus Mode: Chế độ tập trung với Pomodoro timer, block notification và theo dõi năng suất

    **Lợi ích:**
    - Tiết kiệm 30-40% thời gian lập kế hoạch công việc nhờ AI tự động phân loại và ưu tiên
    - Giảm stress do quên deadline: nhận thông báo thông minh và đề xuất điều chỉnh kế hoạch
    - Tăng năng suất làm việc 25% nhờ gợi ý thời gian làm việc hiệu quả nhất
    - Dễ dàng theo dõi tiến độ và phân tích năng suất qua dashboard trực quan

    **Đối thủ cạnh tranh:**
    - Todoist: mạnh về UI/UX nhưng thiếu tính năng AI phân tích thói quen
    - Notion: đa năng nhưng phức tạp, không tối ưu cho quản lý task đơn giản

    USP của TaskMaster Pro: AI cá nhân hóa sâu, học thói quen làm việc và đưa ra gợi ý proactive thay vì chỉ reminder thụ động."""

    print(f"User Input:\n{user_input}\n")

    try:
        # Initialize PO Agent
        print("Initializing PO Agent...")
        po_agent = POAgent(session_id=session_id, user_id=user_id)
        print("✓ PO Agent initialized\n")

        print_separator()
        print("Running PO Agent workflow...")
        print("Note: PO Agent sẽ orchestrate 4 sub agents theo thứ tự:")
        print("  1. Gatherer Agent (Product Brief)")
        print("  2. Vision Agent (Product Vision & PRD)")
        print("  3. Backlog Agent (Product Backlog)")
        print("  4. Priority Agent (Sprint Plan)")
        print_separator()

        # Run PO Agent
        result = po_agent.run(user_input=user_input)

        print_separator()
        print("PO Agent workflow completed!")
        print_separator()

        # Print result summary
        print("\n📊 PO AGENT RESULT:")
        if result and isinstance(result, dict):
            messages = result.get("messages", [])
            print(f"   Total Messages: {len(messages)}")

            # Try to find final outputs in messages
            print(f"\n💬 Message Summary:")
            for i, msg in enumerate(messages[-5:], start=len(messages)-4):
                msg_type = msg.get("type", "unknown") if isinstance(msg, dict) else "unknown"
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                content_preview = content[:100] + "..." if len(str(content)) > 100 else content
                print(f"   [{i}] {msg_type}: {content_preview}")

            print(f"\n✅ PO Agent đã hoàn thành workflow!")
            print(f"   Check Langfuse để xem chi tiết traces và outputs của từng sub agent.")

        else:
            print("No result from PO Agent")
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        return True

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
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

    # Choice menu
    print("\nSelect test to run:")
    print("  1. Test PO Agent (Deep Agent với tool-calling)")
    print("  2. Test Full PO Pipeline (manual orchestration)")
    print("  3. Test individual agents (Gatherer/Vision/Backlog/Priority)")

    choice = input("\nYour choice (1/2/3): ").strip()

    if choice == "1":
        # Test PO Agent
        success = test_po_agent()
    elif choice == "2":
        # Test full PO pipeline
        success = test_full_po_pipeline()
    elif choice == "3":
        # Test individual agents
        print("\nSelect agent to test:")
        print("  1. Gatherer Agent")
        print("  2. Vision Agent")
        print("  3. Backlog Agent")
        print("  4. Priority Agent")

        agent_choice = input("\nYour choice (1/2/3/4): ").strip()

        if agent_choice == "1":
            success = test_gatherer_agent()
        elif agent_choice == "2":
            success = test_vision_agent()
        elif agent_choice == "3":
            success = test_backlog_agent()
        elif agent_choice == "4":
            success = test_priority_agent()
        else:
            print("Invalid choice!")
            return 1
    else:
        print("Invalid choice!")
        return 1

    if success:
        print("\nAll tests completed successfully!")
        return 0
    else:
        print("\nTests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())