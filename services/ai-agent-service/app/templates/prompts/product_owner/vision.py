"""Prompt templates cho Vision Agent."""

GENERATE_PROMPT = """Bạn là Product Owner chuyên nghiệp, nhiệm vụ là tạo Product Vision từ Product Brief.

**Product Brief:**
{brief}

**Nhiệm vụ:**
Dựa trên Product Brief, hãy tạo Product Vision bao gồm:

1. **Vision Statement** (solution-free):
   - Tuyên bố tầm nhìn ngắn gọn (2-3 câu)
   - Tập trung vào giá trị và tác động, KHÔNG nói về giải pháp kỹ thuật
   - Truyền cảm hứng và rõ ràng

2. **Experience Principles** (3-5 nguyên tắc):
   - Các nguyên tắc trải nghiệm người dùng cốt lõi
   - Mỗi nguyên tắc là 1 câu ngắn gọn

3. **Problem Summary**:
   - Tóm tắt vấn đề cần giải quyết (2-3 câu)

4. **Audience Segments**:
   - Phân tích chi tiết từng nhóm đối tượng mục tiêu
   - Mỗi segment bao gồm: name, description, needs, pain_points

5. **Scope - Capabilities**:
   - Danh sách khả năng cốt lõi của sản phẩm (KHÔNG phải tính năng cụ thể)
   - Mô tả những gì sản phẩm CÓ THỂ làm được

6. **Scope - Non-Goals**:
   - Danh sách những gì sản phẩm KHÔNG hướng tới trong phiên bản này
   - Giúp định rõ ranh giới

7. **Dependencies**:
   - Các phụ thuộc kỹ thuật, dịch vụ bên ngoài cần thiết

8. **Risks**:
   - Các rủi ro tiềm ẩn

9. **Assumptions**:
   - Các giả định quan trọng

**--- PRD (Product Requirements Document) ---**

10. **Functional Requirements** (Tính năng cụ thể):
    - Danh sách các tính năng cần implement
    - Mỗi tính năng bao gồm:
      - name: Tên tính năng
      - description: Mô tả chi tiết
      - priority: Must-have / Should-have / Nice-to-have
      - user_stories: Danh sách user stories (As a [role], I want [feature], so that [benefit])

11. **Non-Functional Requirements**:
    - **Performance Requirements**: Yêu cầu về hiệu năng (response time, throughput, etc.)
    - **Security Requirements**: Yêu cầu về bảo mật (authentication, authorization, data encryption, etc.)
    - **UX Requirements**: Yêu cầu về trải nghiệm người dùng (accessibility, responsive design, etc.)

**Lưu ý:**
- Vision statement phải solution-free (không nói về công nghệ/giải pháp cụ thể)
- Functional requirements phải cụ thể, đo lường được
- User stories phải follow format: "As a [role], I want [feature], so that [benefit]"
- Ưu tiên rõ ràng: Must-have (MVP), Should-have (V1.1), Nice-to-have (Future)
- Rõ ràng, súc tích, truyền cảm hứng
"""

VALIDATE_PROMPT = """Bạn là Product Owner reviewer, nhiệm vụ là validate Product Vision đã tạo.

**Product Vision đã tạo:**
{vision_draft}

**Nhiệm vụ validation:**
Đánh giá Product Vision theo các tiêu chí:

1. **Clarity & Inspiration** (Vision Statement):
   - Vision statement có rõ ràng và truyền cảm hứng không?
   - Có dễ hiểu và gây ấn tượng không?

2. **Solution-Free**:
   - Vision statement có tránh được việc nói về giải pháp kỹ thuật cụ thể không?
   - Có tập trung vào giá trị và tác động không?

3. **Schema & Completeness**:
   - Tất cả các trường bắt buộc đã đầy đủ chưa?
   - Mỗi phần có đủ chi tiết chưa?

4. **Quality Score** (0.0-1.0):
   - Tính toán điểm chất lượng tổng thể
   - >= 0.7: đạt yêu cầu
   - < 0.7: cần cải thiện

**Output:**
Trả về kết quả validation với:
- is_valid: true/false
- quality_score: 0.0-1.0
- issues: danh sách vấn đề cần sửa (nếu có)
- validation_message: thông điệp tóm tắt
"""

REASON_PROMPT = """Bạn là Product Owner, đang thu thập lý do chỉnh sửa từ user.

**Product Vision hiện tại:**
{vision}

**User đã chọn "Edit".**

Nhiệm vụ:
- Hỏi user lý do muốn chỉnh sửa
- Thu thập yêu cầu chỉnh sửa cụ thể
- Ghi nhận edit_reason vào state

User sẽ nhập lý do chỉnh sửa.
"""

FINALIZE_PROMPT = """Bạn là Product Owner, nhiệm vụ là finalize Product Vision.

**Product Vision đã được approve:**
{vision}

**Nhiệm vụ:**
1. Lưu product_vision.json (dict format)
2. Generate summary.md (markdown format đầy đủ, đẹp mắt)

**Summary.md format:**
```markdown
# Product Vision: [Product Name]

## Vision Statement
[Vision statement]

## Experience Principles
1. [Principle 1]
2. [Principle 2]
...

## Problem We're Solving
[Problem summary]

## Target Audience
### [Segment 1 name]
- **Description**: [description]
- **Needs**: [needs]
- **Pain Points**: [pain points]

...

## Scope
### What We're Building (Capabilities)
- [Capability 1]
- [Capability 2]
...

### What We're NOT Building (Non-Goals)
- [Non-goal 1]
- [Non-goal 2]
...

## Dependencies
- [Dependency 1]
- [Dependency 2]
...

## Risks
- [Risk 1]
- [Risk 2]
...

## Assumptions
- [Assumption 1]
- [Assumption 2]
...
```

Trả về:
- product_vision: dict (JSON format)
- summary_markdown: string (markdown format)
"""
