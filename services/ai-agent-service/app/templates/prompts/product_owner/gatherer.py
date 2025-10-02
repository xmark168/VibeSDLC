"""Prompt templates cho gatherer agent."""

# Evaluation prompt để đánh giá conversation memory
EVALUATE_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang đánh giá thông tin để tạo product brief.

## Ngữ cảnh cuộc hội thoại:
{messages}

## Nhiệm vụ:
Đánh giá độ đầy đủ của thông tin đã thu thập được để tạo một product brief hoàn chỉnh.

Một product brief hoàn chỉnh cần có:
1. **Tổng quan sản phẩm**: Mục đích, vấn đề cần giải quyết, giá trị cốt lõi
2. **Đối tượng người dùng**: Persona, nhu cầu, pain points
3. **Tính năng chính**: Các tính năng thiết yếu và ưu tiên
4. **Chỉ số thành công**: KPIs, metrics để đo lường
5. **Yêu cầu kỹ thuật**: Platform, công nghệ, constraints
6. **Scope & Timeline**: Phạm vi MVP, các milestone

## Hướng dẫn chấm điểm:
- Nếu thông tin rất ít hoặc không có, score nên < 0.3
- Nếu có đủ thông tin cơ bản nhưng thiếu chi tiết, score 0.3-0.6
- Nếu có nhiều thông tin nhưng còn một vài gaps, score 0.6-0.8
- Chỉ khi có đầy đủ 6 mục trên thì score >= 0.8

Mỗi gap nên cụ thể và actionable. Ví dụ: "Chưa xác định được đối tượng người dùng chính"."""
