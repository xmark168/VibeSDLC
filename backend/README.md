# Backend Service

Backend API service for VibeSDLC application.

## Tech Stack
- FastAPI
- PostgreSQL
- Redis
- SQLModel

## Setup

```bash
# Install dependencies
uv sync

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```



1. Tạo migration mới (autogenerate từ models)
uv run alembic revision --autogenerate -m "add BA workflow models"

2. Áp dụng migration
uv run alembic upgrade head

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

tasklist /FI "IMAGENAME eq python.exe"

taskkill /PID 28080 /T /F

uv run app/tests/test_agent.py

front end netstat -ano | findstr :5173 taskkill /PID 24844 /F

git reset --soft HEAD~1 git rm --cached services/ai-agent-service/.env

deactivate

.venv\Scripts\activate

approve backlog xong thì lưu mới db không, hình  -> cập nhật kanban

next mới lưu

không phải ý tôi là khi tạo

tôi muốn tạo 1 website bán sách, đại khái giống tiki nhưng đơn giản hơn

đang gặp vấn đề là Bán hàng offline gặp hạn chế về mặt bằng, tôi định bán lại sách giấy, website có khách hàng mua sách, trang quản trị danh cho quản lý kho, đơn hàng và nhân viên. tính năng gồm tích hợp thanh toán online, quản lý đơn hàng, hệ thống đánh giá sản phẩm, đánh giá sách, giỏ hàng, thanh toán online, theo dõi đơn hàng. nhóm khách hàng là sinh viên, người đi làm, và mọi đối tượng yêu thích sách. những người sử dụng hệ thống là khách hàng, nhân viên, quản lý kho. thanh toán quét mã qr, nội dung qr là tài khoản ngân hàng của tôi