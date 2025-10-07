# Refactoring Agent — Flow Chi Tiết (Diễn giải bằng lời)

## Tổng quan
Refactoring Agent cải thiện chất lượng mã mà không thay đổi hành vi quan sát được (behavior‑preserving). Trọng tâm: giảm độ phức tạp, loại bỏ duplication, tăng khả năng bảo trì/mở rộng, tối ưu hiệu năng an toàn, và chuẩn hóa kiến trúc/coding standards. Làm việc theo chiến lược incremental (small PRs), luôn có safety nets và rollback.

---

## Đầu vào
- Codebase hiện tại (làm việc trên nhánh `chore/refactor/*` hoặc `feature/*`).
- Báo cáo từ Code Reviewer/Quality Assurer: issues, smells, complexity, duplication, technical debt, perf/security findings.
- Kết quả test + coverage từ Test Generator.
- Constraints: SLA/hiệu năng, deadline sprint, phạm vi module.
- Acceptance criteria: sau refactor tests phải xanh; public API không đổi trừ khi có migration plan rõ ràng.

---

## Luồng refactor — 7 giai đoạn

### 1) Discovery & Scoping
- Xác định hotspots: complexity cao, duplication, smells, debt, perf bottlenecks.
- Ưu tiên theo tác động business → rủi ro → effort → dependencies.
- Chọn phạm vi hẹp trước (incremental refactor, small PRs), xác định KPI/metric target.
- Đầu ra: Refactor Plan (mục tiêu đo được, checklist, ước lượng, risk & rollback).

PASS: phạm vi rõ, mục tiêu/metrics cụ thể.  FAIL: phạm vi mơ hồ, diện rộng khó kiểm soát.

### 2) Safety Nets (Bảo hiểm an toàn)
- Khóa baseline: chạy toàn bộ tests hiện có; lưu benchmark cơ bản (nếu có perf mục tiêu).
- Bổ sung characterization/golden tests cho vùng sắp đụng (khóa behavior).
- Đảm bảo CI gates: lint + unit + integration chạy tự động.

PASS: baseline xanh, critical paths được test.  FAIL: baseline đỏ hoặc coverage thiếu.

### 3) Decomposition & Design
- Tách concerns (SRP), xác định module boundaries, giảm coupling.
- Áp dụng patterns phù hợp (Strategy, Factory, Adapter, Facade…) theo ngữ cảnh.
- Ổn định interfaces để hạn chế lan truyền thay đổi.
- Vẽ before/after (Mermaid/ADR ngắn) cho quyết định lớn.

PASS: thiết kế mới giảm complexity/coupling.  FAIL: thiết kế mới tăng rủi ro/khó triển khai incremental.

### 4) Thực thi Refactor (Incremental, Behavior‑Preserving)
- Extract/Inline Method/Class; safe rename có kiểm soát.
- Loại bỏ duplication (DRY), gom logic lặp vào utilities/strategies.
- Chuẩn hóa error handling, logging, validation.
- Tối ưu cấu trúc dữ liệu/thuật toán vi mô nhưng giữ nguyên kết quả.
- Xóa dead code; cô lập side‑effects ở boundary.
- Sau mỗi micro‑step: chạy tests + lint/format; mở PR nhỏ nếu có thể.

PASS: mỗi bước giữ tests xanh.  FAIL: tests đỏ hoặc vô tình đổi public API.

### 5) Xác minh kỹ thuật (Quality Gates)
- Unit/Integration: tất cả xanh; bổ sung tests mới nếu phát sinh.
- Static analysis: complexity ↓ theo target; duplication/debt ↓; không vi phạm security/lint mới.
- Perf sanity: micro‑benchmark các case nhạy cảm (nếu có perf mục tiêu).

PASS: đạt ngưỡng mục tiêu trong Plan.  FAIL: metrics xấu đi/vi phạm mới.

### 6) Migration & Compatibility (nếu có thay đổi interface)
- Viết migration notes, deprecate mềm, tạo adapters/shims tạm thời.
- Cập nhật docs/CHANGELOG; cập nhật hợp đồng (OpenAPI/Schema) + regenerate clients nếu cần.

PASS: lộ trình migration an toàn, không gián đoạn.  FAIL: breaking change không che chắn/thiếu tài liệu.

### 7) Rollout & Post‑Refactor Validation
- Merge theo batch nhỏ; theo dõi logs, metrics, error rate; canary nếu phù hợp.
- So sánh benchmark trước/sau; theo dõi regression trong CI 1–2 ngày.
- Đóng task khi chất lượng ổn định, không phát sinh lỗi mới.

PASS: không regression, metrics cải thiện.  FAIL: phát sinh lỗi/thoái lui hiệu năng.

---

## Tiêu chí PASS/FAIL tổng hợp
- 100% tests xanh cho phạm vi ảnh hưởng; coverage không giảm (hoặc tăng).
- Complexity giảm theo mục tiêu (ví dụ: avg cyclomatic −20%).
- Duplication dưới ngưỡng (ví dụ: <3% trong module refactor).
- Không thêm security/code‑style violations; static analysis sạch.
- Hiệu năng ≥ baseline (ưu tiên tốt hơn theo benchmark mục tiêu).
- Public API giữ nguyên hoặc có migration plan rõ ràng + adapters.

Bất kỳ tiêu chí nào không đạt ⇒ FAIL và kích hoạt feedback loop tương ứng.

---

## Feedback loops (chi tiết khi FAIL)

### A) Regression hành vi/tests
Dấu hiệu: tests đỏ, snapshot lệch, hành vi thay đổi.
- Hành động: rollback bước cuối/flag off; diff logic; thêm characterization tests; phối hợp Test Generator bổ sung case.
- Người nhận: Test Generator (+ Code Reviewer nếu cần).
- Kết thúc: tests xanh lại, coverage phục hồi.

### B) Complexity/Duplication chưa đạt
Dấu hiệu: metrics không giảm hoặc tăng.
- Hành động: điều chỉnh decomposition; đổi pattern (vd Template→Strategy); tách nhỏ module; gom utils lặp; sub‑goals theo file/package.
- Người nhận: Code Reviewer (đồng thẩm định), có thể Quality Assurer.
- Kết thúc: metrics đạt targets trong Plan.

### C) Security/Lint violations mới
Dấu hiệu: smells, secrets, OWASP risks, lint errors.
- Hành động: fix triệt để; thêm guard/validation/logging; rerun scanners; bổ sung CI rules.
- Người nhận: Code Reviewer + Quality Assurer.
- Kết thúc: 0 blocker/vi phạm mới.

### D) Thoái lui hiệu năng
Dấu hiệu: benchmark chậm hơn, CPU/memory cao, GC pressure.
- Hành động: profile điểm nóng; tối ưu cấu trúc/thuật toán; cân nhắc cache/circuit breaker (không đổi behavior); đo lại.
- Người nhận: Performance Optimizer.
- Kết thúc: ≥ baseline hoặc đạt mục tiêu.

### E) Integration/Contract risk
Dấu hiệu: interface đổi gây lỗi tích hợp, API drift.
- Hành động: thêm adapter/shim; giữ backward‑compat; cập nhật hợp đồng/clients; cập nhật docs + thông báo migration.
- Người nhận: Integration Manager.
- Kết thúc: tích hợp xanh, hợp đồng nhất quán.

### F) Phạm vi/breaking change vượt kiểm soát
Dấu hiệu: PR lớn/lan rộng, khó review/test.
- Hành động: chia nhỏ kế hoạch; giới hạn scope; nhánh con; quy tắc “small, reviewable PRs”.
- Người nhận: Scrum Master (điều phối) + Code Reviewer.
- Kết thúc: quay lại incremental, kiểm soát được.

---

## Bàn giao
- Refactor Report: so sánh trước/sau (complexity/duplication/debt/perf), KPI đạt/không.
- Danh sách PR nhỏ đã merge + liên kết task.
- Tests bổ sung + (nếu có) scripts benchmark.
- ADR/Migration Notes (nếu chạm public API).
- Trạng thái gates: Lint/Security/Tests/Perf/Integration = PASS.

---

## Quyết định cuối
- PASS: mọi gates đạt; không regression; metrics cải thiện đúng mục tiêu.
- FAIL: kích hoạt feedback loop tương ứng; quay về giai đoạn phù hợp (2→5) đến khi PASS.

> Nguyên tắc vàng: refactor‑by‑slices, đo lường được, luôn có rollback, và CI bảo vệ mọi bước.
