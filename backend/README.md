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