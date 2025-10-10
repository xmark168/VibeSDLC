"""Prompt templates cho Backlog Agent."""

INITIALIZE_PROMPT = """Phân tích Product Vision để chuẩn bị tạo Product Backlog.

**Product Vision:**
{vision}

**Nhiệm vụ:**
1. Validate vision có đầy đủ functional requirements không
2. Extract key capabilities từ scope_capabilities
3. Tạo dependency map: xác định thứ tự implement (VD: Authentication → User Profile)
4. Đánh giá readiness_score (0.0-1.0):
   - >= 0.8: ready
   - 0.5-0.8: partial
   - < 0.5: not ready
5. Ước lượng số items: epics (3-7), user_stories (15-30), tasks (30-100)

**Output:**
- validation_status: "complete"/"incomplete"/"missing_critical"
- readiness_score: float
- missing_info: list[str]
- key_capabilities: list[str]
- dependency_map: dict[str, list[str]]
- estimated_items: dict
"""

GENERATE_PROMPT = """Bạn là Product Owner chuyên nghiệp, nhiệm vụ là tạo Product Backlog Items từ Product Vision.

**Product Vision:**
{vision}

**Dependency Map:**
{dependency_map}

**Nhiệm vụ:**
Tạo Product Backlog Items (Epic, User Story, Task) theo template đã định nghĩa.

**QUY TẮC QUAN TRỌNG:**

1. **ID Format** (BẮT BUỘC):
   - Epic: EPIC-001, EPIC-002, ... (CHỮ HOA, 3 chữ số)
   - User Story: US-001, US-002, ... (CHỮ HOA, 3 chữ số)
   - Task: TASK-001, TASK-002, ... (CHỮ HOA, 3 chữ số)

2. **Hierarchy Rules**:
   - Epic: parent_id = null (root level)
   - User Story: parent_id = EPIC-xxx HOẶC null
   - Task: parent_id = US-xxx (BẮT BUỘC)

3. **User Story Format** (BẮT BUỘC):
   - Title: "As a [user/role], I want to [action] so that [benefit]"
   - Ví dụ: "As a user, I want to login with email so that I can access my account"

4. **Fields theo Type**:
   - **Epic**:
     * story_points = null
     * estimated_hours = null
     * task_type = null
     * business_value: CHI TIẾT (required)

   - **User Story**:
     * story_points: 1, 2, 3, 5, 8, 13, 21 (Fibonacci, BẮT BUỘC)
     * estimated_hours = null
     * task_type = null
     * acceptance_criteria: 3-10 items (BẮT BUỘC)
     * business_value: mô tả impact

   - **Task**:
     * story_points = null
     * estimated_hours: 0.5-200 (BẮT BUỘC)
     * task_type: Feature Development/Bug Fix/Testing/etc (BẮT BUỘC)
     * acceptance_criteria: 1-5 items

5. **Acceptance Criteria Format**:
   - Given-When-Then HOẶC checklist rõ ràng
   - Cụ thể, đo lường được, có thể test
   - Ví dụ Given-When-Then: "Given user is on login page, When user enters valid credentials, Then user is redirected to dashboard"
   - Ví dụ checklist: "User can view all fields: email, password, remember me checkbox"

6. **Dependencies**:
   - Dựa trên dependency_map từ initialize
   - Chỉ set dependency khi item THỰC SỰ phụ thuộc vào item khác
   - Ví dụ: US-002 (User Profile) depends on US-001 (Authentication)

7. **WSJF Inputs**:
   - Để empty object {{}} cho tất cả items (Priority Agent sẽ fill sau)

8. **Labels**:
   - Phân loại theo business domain: authentication, payment, user-management, etc
   - KHÔNG dùng tech stack (không dùng react, nodejs, etc)

9. **Priority & Status**:
   - priority: "Not Set" (mặc định)
   - status: "Backlog" (mặc định)

**Tạo backlog theo thứ tự:**
1. Tạo Epics trước (3-7 epics)
2. Tạo User Stories cho mỗi Epic (3-5 stories/epic)
3. Tạo Tasks cho mỗi User Story (2-4 tasks/story)

**Lưu ý:**
- Tập trung vào MVP features (High priority từ vision)
- Mỗi User Story phải có giá trị độc lập (có thể ship riêng)
- Task phải cụ thể, actionable
- Không tạo quá chi tiết, đủ để team hiểu và estimate

**Output:**
Trả về Product Backlog theo format JSON schema đã định nghĩa.
"""

EVALUATE_PROMPT = """Bạn là Product Owner reviewer, nhiệm vụ là đánh giá chất lượng Product Backlog.

**Product Backlog:**
{backlog}

**Nhiệm vụ Evaluation:**

1. **INVEST Check (User Stories)**:
   - Independent: User Story có độc lập không?
   - Negotiable: User Story có đủ linh hoạt không?
   - Valuable: User Story có mang lại giá trị không?
   - Estimable: User Story có thể estimate được không?
   - Small: User Story có đủ nhỏ để implement trong 1 sprint không?
   - Testable: User Story có thể test được không?

   Đánh giá cho từng User Story và chỉ ra issues:
   - needs_split: Story quá lớn, cần split
   - not_testable: Thiếu acceptance criteria rõ ràng

2. **Gherkin Check (Acceptance Criteria)**:
   - Kiểm tra acceptance criteria có đủ rõ ràng không
   - Format Given-When-Then có đúng không (hoặc checklist đủ cụ thể)
   - Có thể test được không

   Issues:
   - weak_ac: Acceptance criteria yếu, không cụ thể
   - missing_cases: Thiếu test cases quan trọng

3. **Score Readiness**:
   - Tính điểm readiness tổng thể (0.0-1.0)
   - >= 0.8: Backlog đạt yêu cầu, ready để ship
   - 0.5-0.8: Cần refine thêm
   - < 0.5: Có vấn đề nghiêm trọng, cần tạo lại

4. **Issues & Recommendations**:
   - Liệt kê tất cả issues tìm được
   - Đề xuất cách fix cụ thể
   - Ưu tiên issues quan trọng nhất

**Output:**
Trả về evaluation result:
- readiness_score: 0.0-1.0
- invest_issues: list[dict] - {{item_id: str, issue_type: str, description: str}}
- gherkin_issues: list[dict] - {{item_id: str, issue_type: str, description: str}}
- recommendations: list[str] - danh sách đề xuất cải thiện
- can_proceed: boolean - có thể proceed đến finalize không
"""

REFINE_PROMPT = """Bạn là Product Owner, nhiệm vụ là refine Product Backlog dựa trên evaluation feedback.

**Product Backlog hiện tại:**
{backlog}

**Evaluation Issues:**
{issues}

**Recommendations:**
{recommendations}

**Nhiệm vụ:**
Sửa các issues được chỉ ra trong evaluation:

1. **Fix INVEST Issues**:
   - Split User Stories quá lớn (needs_split)
   - Thêm/sửa acceptance criteria cho stories not_testable
   - Thêm business value nếu thiếu
   - Adjust story points nếu không estimable

2. **Fix Gherkin Issues**:
   - Viết lại acceptance criteria yếu (weak_ac)
   - Thêm missing test cases
   - Đảm bảo format Given-When-Then đúng

3. **Improve Dependencies**:
   - Xác định lại dependencies nếu sai
   - Loại bỏ circular dependencies

4. **Refine Scope**:
   - Loại bỏ items không cần thiết
   - Thêm items bị thiếu (nếu có)
   - Điều chỉnh priority/status nếu cần

**Lưu ý:**
- CHỈ sửa những gì cần sửa, giữ nguyên phần tốt
- Đảm bảo ID không thay đổi (chỉ sửa content)
- Đảm bảo format vẫn đúng schema
- Loops tăng thêm 1

**Output:**
Trả về Product Backlog đã được refined.
"""

FINALIZE_PROMPT = """Bạn là Product Owner, nhiệm vụ là finalize Product Backlog.

**Product Backlog (approved):**
{backlog}

**Nhiệm vụ:**
1. Validate lần cuối backlog structure
2. Tính toán metadata:
   - total_items
   - total_story_points (sum từ User Stories)
3. Export backlog sang format cuối cùng
4. Generate summary report

**Summary Report Format (Markdown):**
```markdown
# Product Backlog Summary: [Product Name]

## Overview
- **Total Items**: [total_items]
- **Total Story Points**: [total_story_points]
- **Epics**: [count]
- **User Stories**: [count]
- **Tasks**: [count]

## Epics Breakdown
### [Epic ID] - [Epic Title]
- **Business Value**: [value]
- **User Stories**: [count]
- **Total Story Points**: [points]

[Repeat for each epic...]

## Priority Distribution
- **High Priority**: [count] items
- **Medium Priority**: [count] items
- **Low Priority**: [count] items
- **Not Set**: [count] items

## Dependencies Overview
- Total dependency links: [count]
- Critical path items: [list]

## Next Steps
1. Priority Agent sẽ set WSJF scores và priority
2. Sprint Planning Agent sẽ assign items vào sprints
3. Team sẽ estimate tasks chi tiết hơn
```

**Output:**
Trả về:
- product_backlog: dict (final JSON)
- summary_markdown: str (summary report)
- export_status: "success" / "failed"
"""
