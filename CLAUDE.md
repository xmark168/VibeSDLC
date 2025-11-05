# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibeSDLC is a microservices-based software development lifecycle management platform with integrated AI agents. The system uses a peer-to-peer architecture where services communicate through a shared PostgreSQL database and Kafka event streaming. Key features include real-time WebSocket-based chat with AI agents, project/sprint management, automated product backlog generation, and GitHub App integration.

## Architecture

### Microservices Structure

Three independent services with no inter-service dependencies:

1. **Management Service** (Port 8000): Core business logic, user authentication, project/sprint/backlog management [Note: Currently referenced but not fully present in codebase]
2. **AI Agent Service** (Port 8001): AI-powered product owner agent, WebSocket chat, agent orchestration, GitHub integration
3. **Frontend** (Port 5173): React SPA with real-time WebSocket integration

All services connect directly to:
- **PostgreSQL**: Shared database with SQLModel ORM
- **Kafka**: Event streaming (external/self-hosted)
- **Redis**: Optional caching layer

### WebSocket Architecture

Real-time chat implementation in AI Agent Service:

- **Endpoint**: `ws://localhost:8001/api/v1/chat/ws?token={jwt_token}`
- **ConnectionManager**: Per-project connection pooling (app/api/routes/chat_ws.py:23)
- **Authentication**: JWT token via query parameter
- **Keep-alive**: Ping/pong mechanism every 30 seconds
- **Client**: Auto-reconnect with exponential backoff (frontend/src/hooks/useChatWebSocket.ts)
- **Message Persistence**: All messages saved to database with sender tracking
- **Broadcasting**: Messages sent to all connected project members

### AI Agent System

PO Agent implements the Deep Agent pattern using LangGraph to orchestrate 4 specialized sub-agents:

1. **Gatherer Agent**: Collects product information through conversation
2. **Vision Agent**: Creates product vision document
3. **Backlog Agent**: Generates user stories and backlog items
4. **Priority Agent**: Prioritizes items and creates sprint plan

Agent execution available via:
- **WebSocket** (real-time streaming): Messages streamed as agent works
- **REST API** (background/sync): POST `/api/v1/agent/execute` - full results returned when complete

Typical execution time: 1-3 minutes for full workflow.

### GitHub App Integration

- **App ID**: 2115525
- **App Name**: vibesdlc
- **Webhook Endpoint**: `/api/v1/github/webhook` (HMAC-SHA256 verified)
- **Repository Management**: Link GitHub repos to projects
- **Database Models**: `GitHubInstallation` tracks app installations

### Database Models (15 Total)

Key entities (SQLModel with UUID primary keys):

- **User**: Authentication, roles (ADMIN/USER), failed login tracking
- **GitHubInstallation**: GitHub App installation tracking
- **Project**: Workspace with GitHub repo fields (`github_repository_id`, `github_repository_name`)
- **Sprint**: Time-boxed development iteration
- **BacklogItem**: User stories with priority, points, status
- **Message**: Chat history with `AuthorType` (USER/AGENT/SYSTEM)
- **Agent**: Agent execution tracking and results
- **Comment**, **IssueActivity**, **RefreshToken**: Additional models

All models inherit from base with `created_at`, `updated_at` timestamps. Relationships use cascade delete.

### Authentication Flow

JWT-based with token rotation:

1. Login: POST `/api/v1/login/access-token` → access token (30 min) + refresh token (7 days)
2. Token includes: user_id, email, role, family_id (for rotation tracking)
3. Refresh: POST `/api/v1/login/refresh-token` → new token pair
4. WebSocket auth: Token in query param validated before upgrade
5. Lockout: 5 failed attempts → account locked

## Development Commands

### Frontend (React + TypeScript)

```bash
cd frontend
npm install                 # Install dependencies
npm run dev                 # Dev server (localhost:5173)
npm run build               # Production build
npm run preview             # Preview production build
npm run lint                # Biome linting
npm run typecheck           # TypeScript checking
npm run test:e2e            # Playwright E2E tests
npm run test:e2e:ui         # E2E tests with UI
npm run generate-client     # Generate API client from OpenAPI
npm run ci                  # Full check: typecheck + lint + build
npm run analyze             # Bundle analysis
```

### AI Agent Service (FastAPI + LangChain)

```bash
cd services/ai-agent-service

# Install dependencies (uses uv package manager)
uv sync

# Run server
uv run uvicorn app.main:app --reload --port 8001

# Database migrations (Alembic)
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1

# Testing
pytest
uv run pytest app/tests/
```

### All Services (Convenience Scripts)

```bash
# Start all services
bash scripts/start-microservices.sh

# Individual services
bash scripts/run-frontend.sh
bash scripts/run-ai-agent-service.sh
bash scripts/run-management-service.sh

# Build and deploy
bash scripts/build.sh
bash scripts/deploy.sh
```

### Docker Development

```bash
# Local development (includes PostgreSQL)
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d

# Production (external PostgreSQL/Kafka)
docker compose up -d

# Logs
docker compose logs -f ai-agent-service
```

## Key File Locations

### Frontend

- **API Clients**: `frontend/src/apis/` - Auto-generated from OpenAPI specs
- **WebSocket Hook**: `frontend/src/hooks/useChatWebSocket.ts` - Connection lifecycle
- **Routes**: `frontend/src/routes/` - File-based routing (TanStack Router)
- **Components**: `frontend/src/components/` - UI components organized by feature
- **Stores**: `frontend/src/stores/` - Zustand state management
- **Queries**: `frontend/src/queries/` - TanStack Query hooks

### AI Agent Service

- **Main App**: `services/ai-agent-service/app/main.py` - FastAPI entry point
- **Models**: `services/ai-agent-service/app/models.py` - 15 SQLModel database models
- **Schemas**: `services/ai-agent-service/app/schemas.py` - Pydantic schemas
- **WebSocket**: `services/ai-agent-service/app/api/routes/chat_ws.py` - WebSocket implementation
- **Agent Routes**: `services/ai-agent-service/app/api/routes/agent_execution.py` - REST API
- **GitHub Routes**: `services/ai-agent-service/app/api/routes/github_*.py` - GitHub integration
- **PO Agent**: `services/ai-agent-service/app/agents/product_owner/` - AI orchestrator
- **Security**: `services/ai-agent-service/app/core/security.py` - JWT auth
- **Config**: `services/ai-agent-service/app/core/config.py` - Environment settings
- **Migrations**: `services/ai-agent-service/alembic/versions/` - Database migrations

## Testing

### WebSocket Testing

Manual testing files in AI Agent Service root:
- **HTML Client**: `test_websocket.html` - Browser-based testing
- **Python Script**: `test_websocket.py` - Programmatic testing
- **Guide**: `TEST_WEBSOCKET_STEPS.md` - Step-by-step instructions

### Automated Testing

- **Frontend E2E**: `npm run test:e2e` (Playwright)
- **Backend Unit**: `pytest` in service directories
- **Test naming**: Python `test_*.py`, TypeScript `*.spec.ts`

## Environment Configuration

Required environment variables (.env file):

```bash
# Application
PROJECT_NAME=VibeSDLC
ENVIRONMENT=local
DEBUG=true

# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=vibesdlc

# Security
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=11520
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI Services
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=gpt-4.1
DEFAULT_LLM_TEMPERATURE=0.2

# GitHub App
GITHUB_APP_ID=2115525
GITHUB_APP_NAME=vibesdlc
GITHUB_APP_PRIVATE_KEY_PATH=services/ai-agent-service/github_private_key.pem
GITHUB_WEBHOOK_SECRET=webhookvibesdlc

# LangFuse (optional observability)
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Infrastructure
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6379

# CORS (development)
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost:5173
```

## Technology Stack

### Frontend
- **Core**: React 19, TypeScript 5, Vite 7.1
- **UI**: Tailwind CSS 4, Radix UI
- **State**: TanStack Query 5.90 (server), Zustand 5.0 (local)
- **Routing**: TanStack Router 1.132
- **Forms**: React Hook Form 7.63
- **Charts**: Recharts 2.15
- **Linting**: Biome 2.2

### Backend (AI Agent Service)
- **Framework**: FastAPI 0.115, Python 3.13+
- **Package Manager**: uv (ultra-fast Python installer)
- **Database**: SQLModel 0.0.27, Alembic
- **AI/LLM**: LangChain 0.3.13, LangGraph 0.2.62
- **Authentication**: JWT (python-jose), bcrypt
- **GitHub**: PyGithub 2.8.1
- **Rate Limiting**: SlowAPI 0.1.9

## Code Style & Conventions

### Python (Backend)
- **Formatting**: `ruff format`
- **Linting**: `ruff check` + `mypy`
- **Naming**: snake_case functions/variables, PascalCase classes
- **Async**: Use async/await for all route handlers and database operations
- **Type Hints**: Required for all functions

### TypeScript/React (Frontend)
- **Linting**: Biome (`npm run lint`)
- **Type Checking**: tsc (`npm run typecheck`)
- **Naming**: PascalCase components/files, camelCase functions/variables
- **File Routing**: TanStack Router uses file structure
- **Styling**: Tailwind CSS (no CSS-in-JS)

### Commits

Follow Conventional Commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance
- `test:` - Testing
- `docs:` - Documentation
- `refactor:` - Code restructuring

## Common Patterns

### API Client Generation

Frontend API clients are auto-generated from backend OpenAPI specs:

```bash
cd frontend
npm run generate-client  # Updates src/apis/ from backend schemas
```

Always regenerate after backend schema changes.

### Database Operations

Use SQLModel sessions with proper lifecycle:

```python
from app.core.db import get_session
from sqlmodel import Session
from fastapi import Depends

async def create_item(*, session: Session = Depends(get_session)):
    item = Model(...)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item
```

### WebSocket Message Flow

1. Client connects with JWT token
2. ConnectionManager adds to project pool
3. Client sends message → saved to DB → broadcast to all project members
4. Agent processes message → streams responses → saved to DB
5. Ping/pong keep-alive every 30 seconds
6. On disconnect: ConnectionManager removes from pool

### Adding New API Endpoints

1. Create route in `services/ai-agent-service/app/api/routes/new_route.py`
2. Include router in `services/ai-agent-service/app/api/main.py`
3. Define schemas in `app/schemas.py` if needed
4. Run `npm run generate-client` to update frontend API client

### Adding Database Models

1. Define model in `services/ai-agent-service/app/models.py`
2. Create migration: `alembic revision --autogenerate -m "Add model"`
3. Review and run: `alembic upgrade head`
4. Create CRUD operations in `app/crud/model.py`

## API Structure

```
/api/v1/
├── /auth/                       # Authentication
│   ├── POST /login/access-token
│   ├── POST /login/refresh-token
│   └── POST /register
├── /users/                      # User management
├── /projects/                   # Project CRUD
├── /sprints/                    # Sprint management
├── /backlog-items/              # Backlog items
├── /messages/                   # Chat messages
├── /agents/                     # Agent management
├── /chat/ws                     # WebSocket endpoint
├── /agent/execute               # Agent execution
└── /github/                     # GitHub integration
    ├── POST /webhook
    ├── GET /repositories
    └── POST /repositories
```

## Documentation References

- `README.md` - Project overview, deployment modes
- `AGENTS.md` - Repository guidelines and agent details
- `GITHUB_APP_INTEGRATION.md` - GitHub integration documentation
- `TEST_WEBSOCKET_STEPS.md` - WebSocket testing guide
- `frontend/README.md` - Frontend-specific setup
- OpenAPI docs: `http://localhost:8001/docs` (when running)