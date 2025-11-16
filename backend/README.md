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
