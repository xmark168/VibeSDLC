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

**Output:**
- validation_status: "complete"/"incomplete"/"missing_critical"
- readiness_score: float
- missing_info: list[str]
- key_capabilities: list[str]
- dependency_map: dict[str, list[str]]
"""

GENERATE_PROMPT = """Bạn là Product Owner chuyên nghiệp, nhiệm vụ là tạo Product Backlog Items từ Product Vision.

**Product Vision:**
{vision}

**Nhiệm vụ:**
Tạo Product Backlog Items (Epic, User Story, Task, Sub-task) theo template đã định nghĩa.

**QUY TẮC QUAN TRỌNG:**

1. **ID Format** (BẮT BUỘC):
   - Epic: EPIC-001, EPIC-002, ... (CHỮ HOA, 3 chữ số)
   - User Story: US-001, US-002, ... (CHỮ HOA, 3 chữ số)
   - Task: TASK-001, TASK-002, ... (CHỮ HOA, 3 chữ số)
   - Sub-task: SUB-001, SUB-002, ... (CHỮ HOA, 3 chữ số)

2. **Hierarchy Rules (THEO JIRA)** (BẮT BUỘC):
   - Epic: parent_id = null (root level, container cho các work items)
   - User Story: parent_id = EPIC-xxx (standard work item, con của Epic)
   - Task: parent_id = EPIC-xxx (standard work item, con của Epic, CÙNG CẤP với User Story)
   - Sub-task: parent_id = US-xxx HOẶC TASK-xxx (con của User Story hoặc Task, để chia nhỏ work)

3. **User Story Format** (BẮT BUỘC):
   - Title: "As a [user/role], I want to [action] so that [benefit]"
   - Ví dụ: "As a user, I want to login with email so that I can access my account"

4. **Description Field** (BẮT BUỘC cho TẤT CẢ items):
   - Epic: Mô tả chi tiết về epic này (20-100 từ)
   - User Story: Mô tả context, background (10-50 từ)
   - Task: Mô tả high-level technical approach (10-50 từ)
   - Sub-task: Mô tả cụ thể implementation details (5-30 từ)

5. **Fields theo Type**:
   - **Epic**:
     * story_point = null
     * estimate_value = null
     * task_type = null
     * business_value: CHI TIẾT (required)

   - **User Story**:
     * story_point: 1, 2, 3, 5, 8, 13, 21 (Fibonacci, BẮT BUỘC)
     * estimate_value = null
     * task_type = null
     * acceptance_criteria: 3-10 items (BẮT BUỘC)
     * business_value: mô tả impact

   - **Task** (Standard work item cùng cấp với User Story):
     * story_point = null
     * estimate_value = null (KHÔNG estimate ở Task level)
     * task_type: "Development", "Research", "Infrastructure" (BẮT BUỘC)
     * acceptance_criteria: 2-5 items (high-level definition of done)
     * business_value = null
     * **LƯU Ý**: Task là work item độc lập hoặc technical task không fit user story format

   - **Sub-task** (Con của User Story hoặc Task):
     * story_point = null
     * estimate_value: 0.5-40 hours (BẮT BUỘC)
     * task_type: "Development", "Testing", "Documentation" (BẮT BUỘC)
     * acceptance_criteria: 1-3 items (specific implementation checklist)
     * business_value = null
     * **LƯU Ý**: Sub-task là đơn vị nhỏ nhất, cụ thể, actionable cho 1 developer

6. **Acceptance Criteria Format**:
   - User Story & Task: Given-When-Then format (high-level)
   - Sub-task: Checklist cụ thể (implementation steps)
   - Cụ thể, đo lường được, có thể test
   - Ví dụ Given-When-Then: "Given user is on login page, When user enters valid credentials, Then user is redirected to dashboard"
   - Ví dụ checklist (Sub-task): "API endpoint accepts POST /auth/login", "JWT token generated with 24h expiry", "Error messages returned for invalid credentials"

7. **Dependencies**:
   - Phân tích vision để xác định dependencies giữa các items
   - Chỉ set dependency khi item THỰC SỰ phụ thuộc vào item khác
   - Ví dụ: US-002 (User Profile) depends on US-001 (Authentication)

8. **Labels**:
   - Phân loại theo business domain: authentication, payment, user-management, etc
   - KHÔNG dùng tech stack (không dùng react, nodejs, etc)

9. **Rank & Status**:
    - rank: null (Priority Agent sẽ fill)
    - status: "Backlog" (mặc định)

**Tạo backlog theo thứ tự:**
1. Tạo Epics trước (3-5 epics) - Container cho các work items
2. Tạo User Stories cho mỗi Epic (2-4 stories/epic):
   - parent_id = EPIC-xxx
   - Có story_point
   - Có acceptance criteria (Given-When-Then)
3. (Optional) Tạo Tasks độc lập nếu cần (technical tasks không fit user story):
   - parent_id = EPIC-xxx (cùng cấp với User Story)
   - KHÔNG có estimate_value (estimate ở Sub-task level)
4. Tạo Sub-tasks để chia nhỏ User Stories hoặc Tasks:
   - parent_id = US-xxx hoặc TASK-xxx
   - Có estimate_value (hours)
   - Có task_type (Development/Testing/Documentation)
   - CHỈ tạo Development sub-tasks, KHÔNG tạo Testing (QA Agent sẽ tạo sau)

**Lưu ý:**
- Tập trung vào MVP features (High priority từ vision)
- Mỗi User Story phải có giá trị độc lập (có thể ship riêng)
- Sub-task phải cụ thể, actionable, mô tả rõ cần code gì
- Mỗi Sub-task nên có estimate 0.5-16 hours (không quá lớn)
- Task (nếu tạo) dùng cho technical work không fit user story format (VD: setup infrastructure, research spike)

**Output JSON Format:**
{{{{
  "metadata": {{{{
    "product_name": "..."
  }}}},
  "items": [
    {{{{
      "id": "EPIC-001",
      "type": "Epic",
      "parent_id": null,
      "title": "Authentication System",
      "description": "Complete user authentication system including login, registration, password management",
      "rank": null,
      "status": "Backlog",
      "story_point": null,
      "estimate_value": null,
      "acceptance_criteria": [],
      "dependencies": [],
      "labels": ["core", "authentication"],
      "task_type": null,
      "business_value": "Enable user identification and secure access to application features",
    }}}},
    {{{{
      "id": "US-001",
      "type": "User Story",
      "parent_id": "EPIC-001",
      "title": "As a user, I want to login with email and password so that I can access my account",
      "description": "User authentication using email/password credentials with session management",
      "rank": null,
      "status": "Backlog",
      "story_point": 5,
      "estimate_value": null,
      "acceptance_criteria": [
        "Given user is on login page, When user enters valid credentials, Then user is redirected to dashboard",
        "Given user enters invalid credentials, When user submits login form, Then error message is displayed",
        "Given user is logged in, When user closes browser and returns, Then session is maintained for 24 hours"
      ],
      "dependencies": [],
      "labels": ["authentication", "core"],
      "task_type": null,
      "business_value": "Allow users to securely access their personalized content",
    }}}},
    {{{{
      "id": "SUB-001",
      "type": "Sub-task",
      "parent_id": "US-001",
      "title": "Implement login API endpoint",
      "description": "Create POST /api/auth/login endpoint with email/password validation and JWT generation",
      "rank": null,
      "status": "Backlog",
      "story_point": null,
      "estimate_value": 8.0,
      "acceptance_criteria": [
        "API endpoint accepts POST /api/auth/login with email and password",
        "Valid credentials return JWT token with 24h expiry",
        "Invalid credentials return 401 status with error message",
        "Password is validated using bcrypt"
      ],
      "dependencies": [],
      "labels": ["backend", "authentication"],
      "task_type": "Development",
      "business_value": null,
    }}}},
    {{{{
      "id": "SUB-002",
      "type": "Sub-task",
      "parent_id": "US-001",
      "title": "Create login form UI component",
      "description": "Build React login form component with email, password fields and validation",
      "rank": null,
      "status": "Backlog",
      "story_point": null,
      "estimate_value": 6.0,
      "acceptance_criteria": [
        "Form has email and password input fields",
        "Client-side validation for email format",
        "Submit button disabled until form is valid",
        "Loading state shown during API call"
      ],
      "dependencies": ["SUB-001"],
      "labels": ["frontend", "authentication"],
      "task_type": "Development",
      "business_value": null,
    }}}},
    {{{{
      "id": "TASK-001",
      "type": "Task",
      "parent_id": "EPIC-001",
      "title": "Setup authentication infrastructure",
      "description": "Configure JWT library, session management, and security middleware",
      "rank": null,
      "status": "Backlog",
      "story_point": null,
      "estimate_value": null,
      "acceptance_criteria": [
        "JWT library installed and configured",
        "Authentication middleware implemented",
        "Environment variables configured for secrets"
      ],
      "dependencies": [],
      "labels": ["infrastructure", "authentication"],
      "task_type": "Infrastructure",
      "business_value": null,
    }}}}
  ]
}}}}

**IMPORTANT:** Return ONLY valid JSON matching the schema above. No markdown code blocks, no comments, no explanations.
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
   - total_items: tổng số items
   - total_story_points: sum story points từ tất cả User Stories
3. Export backlog sang format cuối cùng

**Output:**
Trả về final product_backlog dict với:
- metadata: {{product_name, version, total_items, total_story_points, export_status}}
- items: list of all backlog items
"""
