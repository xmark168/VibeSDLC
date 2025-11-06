"""Prompt templates cho Priority Agent."""

CALCULATE_PRIORITY_PROMPT = """Bạn là Product Owner chuyên nghiệp. Phân tích các backlog items sau và chấm điểm theo phương pháp WSJF (Weighted Shortest Job First) để sắp xếp ưu tiên.

**Sản phẩm:** {product_name}

**Các items cần chấm điểm:**
{items_json}

{user_feedback_section}

**Nhiệm vụ:**
Với mỗi item, phân tích business_value description và chấm điểm các yếu tố WSJF (thang điểm 1-10):

1. **Business Value (BV)** - Giá trị kinh doanh: Item này mang lại bao nhiêu giá trị? (1=thấp, 10=rất quan trọng)
   - Epic/User Story: dựa trên mô tả business_value
   - Task: thường ở mức trung bình (5-7) trừ khi là infrastructure quan trọng

2. **Time Criticality (TC)** - Tính cấp bách: Mức độ khẩn cấp? Có cơ hội nhạy cảm về thời gian? (1=có thể đợi, 10=rất gấp)

3. **Risk Reduction/Opportunity Enablement (RR)** - Giảm rủi ro/Mở khóa cơ hội: Item này giảm rủi ro hoặc mở khóa các tính năng khác? (1=ít ảnh hưởng, 10=quan trọng)
   - Kiểm tra dependencies: nếu items khác phụ thuộc vào item này, tăng điểm RR

4. **Job Size** - Khối lượng công việc: Ước lượng effort (thang Fibonacci 1-13):
   - Epic: dựa trên scope mô tả (thường 8-13)
   - User Story: sử dụng story_point có sẵn, nếu không có thì ước lượng từ description
   - Task: ước lượng từ description (thường 3-8)

**Hướng dẫn chấm điểm:**
- **Core/Foundation features** (tính năng nền tảng): BV cao (8-10), RR cao (7-9) nếu features khác phụ thuộc
- **User-facing value** (giá trị trực tiếp cho người dùng): BV cao (7-10), TC tùy vào nhu cầu thị trường
- **Nice-to-have** (tính năng phụ): BV thấp (3-5), TC thấp (2-4)
- **Security/Infrastructure Tasks** (bảo mật/hạ tầng): RR cao (8-10), BV trung bình (5-7)
- **Dependencies** (phụ thuộc): Nếu items khác phụ thuộc vào item này, tăng RR
- **Technical Tasks** (tasks kỹ thuật): BV trung bình (5-7) trừ khi rất quan trọng

**QUAN TRỌNG:** Nếu có user feedback ở trên, bạn PHẢI điều chỉnh điểm WSJF theo feedback.
Ví dụ:
- "Tăng priority cho EPIC-002" → Tăng BV/TC/RR hoặc giảm Job Size cho EPIC-002
- "Giảm priority cho US-001" → Giảm BV/TC/RR hoặc tăng Job Size cho US-001
- "US-003 quan trọng hơn" → Tăng BV/TC cho US-003

**Output JSON Format:**
{{
  "wsjf_scores": [
    {{
      "item_id": "EPIC-001",
      "business_value": 9,
      "time_criticality": 8,
      "risk_reduction": 8,
      "job_size": 13,
      "reasoning": "Tính năng nền tảng cho quản lý task. Rất quan trọng cho MVP."
    }},
    ...
  ]
}}

**LƯU Ý:** Chỉ trả về JSON hợp lệ. Không dùng markdown, không giải thích bên ngoài JSON.
"""


EVALUATE_SPRINT_PLAN_PROMPT = """Bạn là Scrum Master chuyên nghiệp. Đánh giá sprint plan sau về chất lượng và khả thi.

**Sprint Plan:**
{sprint_plan_json}

**Cấu hình Sprint:**
- Thời lượng Sprint: {sprint_duration_weeks} tuần
- Năng lực Sprint (Capacity): {sprint_capacity} story points

**Nhiệm vụ:**
Đánh giá sprint plan và xác định vấn đề trong các khía cạnh sau:

1. **Vấn đề về Năng lực (Capacity Issues):**
   - **Overload** (quá tải): Sprint vượt quá capacity (velocity_plan > {sprint_capacity})
   - **Underload** (dưới tải): Sprint sử dụng ít hơn nhiều capacity (velocity_plan < 70% capacity)
   - Kiểm tra velocity_plan của từng sprint so với capacity

2. **Vấn đề về Phụ thuộc (Dependency Issues):**
   - Kiểm tra xem các items có được gán vào sprints đúng thứ tự dựa trên dependencies không
   - Item chỉ nên ở sprint N nếu tất cả dependencies của nó ở sprint < N
   - Sử dụng dependency graph từ prioritized_backlog

3. **Sẵn sàng cho MVP (MVP Readiness - Kiểm tra Sprint 1):**
   - Sprint 1 có chứa các items quan trọng nhất (WSJF cao nhất) không?
   - Các tính năng nền tảng/cốt lõi có ở sprints đầu không?
   - Kiểm tra xem MVP (sản phẩm khả dụng tối thiểu) có thể deliver được ở sprint 1-2 không

4. **Kiểm tra Cân bằng (Balance Check):**
   - Các sprints có cân bằng hợp lý về khối lượng công việc không?
   - Có sprint nào có quá nhiều items so với các sprint khác không?

**Tiêu chí chấm điểm:**
- **1.0**: Kế hoạch hoàn hảo (không có vấn đề, cân bằng tốt, sẵn sàng cho MVP)
- **0.8-0.9**: Kế hoạch tốt (vấn đề nhỏ, chấp nhận được)
- **0.6-0.7**: Cần cải thiện (một số vấn đề cần sửa)
- **0.5 trở xuống**: Cần điều chỉnh lại (vấn đề nghiêm trọng)

**Output JSON Format:**
{{
  "readiness_score": 0.85,
  "can_proceed": true,
  "capacity_issues": [
    {{
      "sprint_id": "sprint-2",
      "issue_type": "overload",
      "description": "Sprint 2 bị quá tải: 45 points so với capacity 30",
      "severity": "high"
    }}
  ],
  "dependency_issues": [
    {{
      "item_id": "US-005",
      "sprint_id": "sprint-1",
      "issue_type": "dependency_not_met",
      "description": "US-005 phụ thuộc vào EPIC-001 nhưng EPIC-001 lại ở sprint-2",
      "severity": "critical"
    }}
  ],
  "recommendations": [
    "Chuyển US-003 từ sprint-2 sang sprint-3 để cân bằng capacity",
    "Đảm bảo EPIC-001 hoàn thành trước khi US-005 bắt đầu",
    "Sprint 1 nên tập trung vào authentication và database setup"
  ]
}}

**LƯU Ý:**
- Set `can_proceed: true` nếu readiness_score >= 0.8
- Set `can_proceed: false` nếu readiness_score < 0.8
- Chỉ trả về JSON hợp lệ. Không dùng markdown, không giải thích bên ngoài JSON.
"""


REFINE_SPRINT_PLAN_PROMPT = """Bạn là Scrum Master chuyên nghiệp. Điều chỉnh sprint plan bằng cách sửa các vấn đề đã xác định.

**Sprint Plan hiện tại:**
{sprint_plan_json}

**Cấu hình Sprint:**
- Thời lượng Sprint: {sprint_duration_weeks} tuần
- Năng lực Sprint (Capacity): {sprint_capacity} story points

**Các vấn đề cần sửa:**
{issues_json}

**Đề xuất:**
{recommendations}

**Nhiệm vụ:**
Sửa các vấn đề bằng cách điều chỉnh phân công sprint. Tuân theo các quy tắc sau:

1. **Sửa vấn đề Capacity:**
   - **Overload** (quá tải): Chuyển các items có priority thấp hơn (WSJF thấp) sang sprint tiếp theo
   - **Underload** (dưới tải): Kéo các items có priority cao hơn từ sprint tiếp theo nếu dependencies cho phép
   - Mục tiêu: 80-100% capacity utilization cho mỗi sprint

2. **Sửa vấn đề Dependency:**
   - Chuyển items sang sprints sau nếu dependencies của chúng chưa hoàn thành
   - Đảm bảo chuỗi phụ thuộc: item ở sprint N → tất cả dependencies ở sprint < N
   - Quan trọng: KHÔNG BAO GIỜ gán item trước khi dependencies hoàn thành

3. **Cân bằng Sprints:**
   - Phân bố khối lượng công việc đều giữa các sprints
   - Giữ các items liên quan (cùng Epic) ở các sprints gần nhau khi có thể
   - Giữ items có priority cao ở sprints đầu

4. **Giữ nguyên Priority:**
   - Giữ items có WSJF cao nhất ở sprints sớm nhất có thể
   - Chỉ di chuyển items khi cần thiết để sửa vấn đề
   - Ghi lại items nào đã được di chuyển và lý do

**Output JSON Format:**
{{
  "refined_sprints": [
    {{
      "sprint_id": "sprint-1",
      "sprint_number": 1,
      "sprint_goal": "Sprint goal đã cập nhật nếu cần",
      "start_date": "2025-10-13",
      "end_date": "2025-10-27",
      "velocity_plan": 28,
      "velocity_actual": 0,
      "assigned_items": ["EPIC-001", "US-001", "US-002"],
      "status": "Planned"
    }}
  ],
  "changes_made": [
    "Chuyển US-005 từ sprint-1 sang sprint-2 do phụ thuộc vào EPIC-001",
    "Chuyển TASK-003 từ sprint-2 sang sprint-1 để cân bằng capacity (sprint-2 bị quá tải)"
  ],
  "issues_fixed": {{
    "capacity_issues": 2,
    "dependency_issues": 1
  }}
}}

**LƯU Ý:**
- Trả về TOÀN BỘ danh sách refined_sprints (tất cả sprints, không chỉ những sprint thay đổi)
- Duy trì numbering và tính liên tục về ngày tháng của sprint
- Mỗi sprint phải có velocity_plan cập nhật dựa trên assigned_items mới
- Chỉ trả về JSON hợp lệ. Không dùng markdown, không giải thích bên ngoài JSON.
"""


ADJUST_SPRINT_PLAN_PROMPT = """Bạn là Scrum Master chuyên nghiệp. Điều chỉnh sprint plan dựa trên phản hồi từ người dùng.

**Sprint Plan hiện tại:**
{sprint_plan_json}

**Prioritized Backlog:**
{prioritized_backlog_json}

**Cấu hình Sprint:**
- Thời lượng Sprint: {sprint_duration_weeks} tuần
- Năng lực Sprint (Capacity): {sprint_capacity} story points

**Phản hồi từ người dùng (PHẢI TUÂN THEO):**
{user_feedback}

**Nhiệm vụ:**
Điều chỉnh sprint plan theo phản hồi của người dùng. Tuân theo các quy tắc sau:

1. **Hiểu phản hồi:**
   - "Tạo thêm sprint mới" → Tạo thêm sprints bằng cách chia các items
   - "Chuyển item X sang sprint Y" → Di chuyển items cụ thể giữa các sprints
   - "Tạo 2 sprints" → Chia items hiện tại thành 2 sprints
   - "Cân bằng lại" → Phân bố lại items đều giữa các sprints

2. **Tạo Sprints mới:**
   - Nếu người dùng muốn nhiều sprints hơn, chia items ra nhiều sprints
   - Nhắm đến 70-90% capacity utilization cho mỗi sprint
   - Duy trì thứ tự priority: items có rank cao hơn ở sprints sớm hơn
   - Tôn trọng dependencies: dependencies phải ở sprints sớm hơn hoặc cùng sprint

3. **Di chuyển Items:**
   - Di chuyển items theo yêu cầu của người dùng
   - Tính lại velocity_plan cho các sprints bị ảnh hưởng
   - Kiểm tra dependencies sau khi di chuyển

4. **Ngày tháng Sprint:**
   - Mỗi sprint dài {sprint_duration_weeks} tuần
   - Ngày bắt đầu của sprint N+1 = ngày kết thúc của sprint N
   - Sprint đầu tiên bắt đầu từ ngày hiện tại trong plan có sẵn

5. **Sprint Goals:**
   - Cập nhật sprint_goal để phản ánh các items trong mỗi sprint
   - Sử dụng format: "Sprint N: [tóm tắt ngắn gọn các tính năng chính]"

**Output JSON Format:**
{{
  "adjusted_sprints": [
    {{
      "sprint_id": "sprint-1",
      "sprint_number": 1,
      "sprint_goal": "Các tính năng quản lý task cốt lõi",
      "start_date": "2025-10-13",
      "end_date": "2025-10-27",
      "velocity_plan": 25,
      "velocity_actual": 0,
      "assigned_items": ["US-001", "US-002", "EPIC-001"],
      "status": "Planned"
    }},
    {{
      "sprint_id": "sprint-2",
      "sprint_number": 2,
      "sprint_goal": "Tính năng cộng tác dự án và AI",
      "start_date": "2025-10-28",
      "end_date": "2025-11-10",
      "velocity_plan": 15,
      "velocity_actual": 0,
      "assigned_items": ["US-004", "US-007"],
      "status": "Planned"
    }}
  ],
  "changes_made": [
    "Tạo 2 sprints thay vì 1 dựa trên phản hồi người dùng",
    "Chuyển US-004, US-007 sang sprint-2 để cân bằng khối lượng công việc",
    "Sprint 1 tập trung vào tính năng cốt lõi, Sprint 2 vào cộng tác và AI"
  ]
}}

**LƯU Ý:**
- Bạn PHẢI tuân theo phản hồi của người dùng một cách chính xác
- Trả về TOÀN BỘ danh sách adjusted_sprints (tất cả sprints)
- Tính velocity_plan chính xác (tổng story_point của User Stories, Epic/Task không tính)
- Duy trì numbering sprint: 1, 2, 3, ...
- Tính ngày tháng chính xác dựa trên sprint_duration_weeks
- Chỉ trả về JSON hợp lệ. Không dùng markdown, không giải thích bên ngoài JSON.
"""
