Testcase gatherer:

TH1: unclear

Câu hỏi:
Bạn có thể cho biết tên dự kiến của ứng dụng AI này là gì không? (Nếu chưa có, bạn có thể mô tả ngắn gọn ý tưởng tên hoặc chủ đề chính)

-> SmartTask

Ứng dụng AI này sẽ hướng đến nhóm đối tượng người dùng nào? (Ví dụ: sinh viên, nhân viên văn phòng, doanh nghiệp nhỏ, người dùng phổ thông, v.v.)

-> sinh viên, nhân viên văn phòng, freelancer

Theo bạn, ứng dụng AI này sẽ mang lại những lợi ích nổi bật nào cho người dùng? (Ví dụ: tiết kiệm thời gian, tăng hiệu suất công việc, hỗ trợ ra quyết định, v.v.)

-> tiết kiệm thời gian, tăng hiệu suất công việc, hỗ trợ ra quyết định

Bạn có thể mô tả chi tiết cách ứng dụng SmartTask hoạt động không? (Ví dụ: quy trình sử dụng, các bước chính, trải nghiệm người dùng)

-> skip

Theo bạn, những tính năng AI nào là quan trọng nhất mà SmartTask cần có để hỗ trợ sinh viên, nhân viên văn phòng và freelancer? Bạn có thể liệt kê 3-5 tính năng mong muốn.

-> quản lý công việc, quản lý dự án, thông báo deadline, chatbot hỗ trợ

Bạn biết hoặc tham khảo những sản phẩm nào đang cạnh tranh trực tiếp hoặc gián tiếp với SmartTask? Nếu có, bạn có thể nêu tên và điểm mạnh/yếu của họ không?

-> đối thủ cạnh tranh là Trello

Bạn có thể mô tả ngắn gọn cách ứng dụng SmartTask hoạt động từ góc nhìn người dùng không? (Ví dụ: quy trình sử dụng, các bước chính, trải nghiệm khi quản lý công việc/dự án)

-> skip

Theo bạn, điểm khác biệt nổi bật nhất của SmartTask so với Trello là gì? (Ví dụ: tính năng AI, giao diện, trải nghiệm người dùng, v.v.)

-> tính năng AI, giao diện hiện đại


 Các lệnh Alembic thường dùng:

  # 1. Tạo migration mới (autogenerate từ models)
  alembic revision --autogenerate -m "Description of changes"

  # 2. Áp dụng migration
  alembic upgrade head          # Upgrade lên version mới nhất
  alembic upgrade +1            # Upgrade lên 1 version
  alembic upgrade <revision>    # Upgrade đến revision cụ thể

  # 3. Rollback migration
  alembic downgrade -1          # Rollback 1 version
  alembic downgrade base        # Rollback về trạng thái ban đầu

  # 4. Xem history
  alembic history               # Xem tất cả migrations
  alembic current               # Xem version hiện tại

  # 5. Tạo migration thủ công (không autogenerate)
  alembic revision -m "Manual migration"

================================================================

  1. API Comments (comments.py) - ƯU TIÊN CAO

  Kanban board cần comment cho từng card/item:
  - GET /api/v1/comments?backlog_item_id={id} - Lấy comments của item
  - POST /api/v1/comments - Tạo comment mới
  - PATCH /api/v1/comments/{id} - Sửa comment
  - DELETE /api/v1/comments/{id} - Xóa comment

  2. API Sprints (sprints.py) - ƯU TIÊN CAO

  Kanban board phụ thuộc vào sprint:
  - GET /api/v1/projects/{project_id}/sprints - Lấy danh sách sprints
  - GET /api/v1/sprints/{id} - Chi tiết sprint
  - POST /api/v1/sprints - Tạo sprint mới
  - PATCH /api/v1/sprints/{id} - Cập nhật sprint
  - DELETE /api/v1/sprints/{id} - Xóa sprint

  3. API Projects (projects.py) - ƯU TIÊN TRUNG BÌNH

  Để quản lý projects chứa sprints:
  - GET /api/v1/projects - Lấy danh sách projects
  - GET /api/v1/projects/{id} - Chi tiết project
  - POST /api/v1/projects - Tạo project mới
  - PATCH /api/v1/projects/{id} - Cập nhật project
  - DELETE /api/v1/projects/{id} - Xóa project
  - GET /api/v1/projects/{id}/members - Lấy members (cho assign)

  4. API Issue Activities (issue_activities.py) - ƯU TIÊN THẤP

  Để xem lịch sử thay đổi của items:
  - GET /api/v1/backlog-items/{item_id}/activities - Lấy lịch sử

  ---
  Khuyến nghị thứ tự làm:

  1. Sprints API       (Vì backlog_items đã depend vào sprint)
  2. Comments API      (Để có thể comment trong kanban cards)
  3. Projects API      (Để quản lý projects và members)
  4. Issue Activities  (Để xem history - optional)

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

tasklist /FI "IMAGENAME eq python.exe"

taskkill /PID 23360 /T /F

uv run app/tests/test_agent.py 

front end 
netstat -ano | findstr :5173
taskkill /PID 24844 /F

