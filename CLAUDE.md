# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibeSDLC is a microservices-based software development lifecycle management platform with integrated AI agents. The system uses a peer-to-peer architecture where services communicate through a shared PostgreSQL database and Kafka event streaming. Key features include real-time WebSocket-based chat with AI agents, project/sprint management, and automated product backlog generation.

## Architecture

### Microservices Structure

Three independent services with no inter-service dependencies:

1. **Management Service** (Port 8000): Core business logic, user authentication, project/sprint/backlog management
2. **AI Agent Service** (Port 8001): AI-powered product owner agent, WebSocket chat, agent orchestration
3. **Frontend** (Port 5173): React SPA with real-time WebSocket integration

All services connect directly to:
- **PostgreSQL**: Shared database with SQLModel ORM
- **Kafka**: Event streaming (external/self-hosted)

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

PO Agent orchestrates 4 specialized sub-agents using LangGraph:

1. **Gatherer Agent**: Collects product information through conversation
2. **Vision Agent**: Creates product vision document
3. **Backlog Agent**: Generates user stories and backlog items
4. **Priority Agent**: Prioritizes items and creates sprint plan

Agent execution available via:
- **WebSocket** (real-time streaming): POST `/api/v1/chat/ws` - messages streamed as agent works
- **REST API** (background/sync): POST `/api/v1/agent/execute` - full results returned when complete

Typical execution time: 1-3 minutes for full workflow.

### Database Models

Key entities (SQLModel with UUID primary keys):

- **User**: Authentication, roles (ADMIN/USER), failed login tracking
- **Project**: Workspace containing sprints and backlog items
- **Sprint**: Time-boxed development iteration
- **BacklogItem**: User stories with priority, points, status
- **Message**: Chat history (user/agent messages)
- **Agent**: Agent execution tracking and results

Relationships use cascade delete. All models inherit from base with `created_at`, `updated_at` timestamps.

### Authentication Flow

JWT-based with token rotation:

1. Login: POST `/api/v1/login/access-token` → access token (30 min) + refresh token (7 days)
2. Token includes: user_id, email, role, family_id (for rotation tracking)
3. Refresh: POST `/api/v1/login/refresh-token` → new token pair
4. WebSocket auth: Token in query param validated before upgrade
5. Lockout: 5 failed attempts → account locked (failed_login_attempts field)

Token validation in both services (management-service/app/core/security.py:45, ai-agent-service/app/core/security.py:38).

## Development Commands

### Frontend (React + TypeScript)

```bash
cd frontend
npm install                 # Install dependencies
npm run dev                 # Dev server (localhost:5173)
npm run build               # Production build
npm run lint                # Biome linting
npm run typecheck           # TypeScript checking
npm run test:e2e            # Playwright E2E tests
npm run test:e2e:ui         # E2E tests with UI
npm run generate-client     # Generate API client from OpenAPI
npm run ci                  # Full check: typecheck + lint + build
```

### Management Service (FastAPI + SQLModel)

```bash
cd services/management-service

# Testing & Quality
bash scripts/test.sh        # pytest with coverage
bash scripts/lint.sh        # mypy + ruff linting
bash scripts/format.sh      # ruff fix + format

# Run locally
uvicorn app.main:app --reload --port 8000

# Database migrations (Alembic)
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1
```

### AI Agent Service (FastAPI + LangChain)

```bash
cd services/ai-agent-service

# Install dependencies (uses uv)
uv sync

# Run server
uv run uvicorn app.main:app --reload --port 8001

# Testing
pytest
uv run app/tests/test_agent.py
```

### All Services (Convenience Scripts)

```bash
# Start all services
bash scripts/start-microservices.sh

# Individual services
bash scripts/run-frontend.sh
bash scripts/run-management-service.sh
bash scripts/run-ai-agent-service.sh
```

### Docker Development

```bash
# Local development (includes PostgreSQL)
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d

# Production (external PostgreSQL/Kafka)
docker compose up -d

# Logs
docker compose logs -f management-service
docker compose logs -f ai-agent-service
```

## Key File Locations

### Frontend

- **API Clients**: `frontend/src/apis/` - Auto-generated from OpenAPI specs
- **WebSocket Hook**: `frontend/src/hooks/useChatWebSocket.ts` - Manages WebSocket connection lifecycle
- **Routes**: `frontend/src/routes/` - File-based routing (TanStack Router)
- **Components**: `frontend/src/components/` - Shared UI components
- **Queries**: `frontend/src/queries/` - TanStack Query hooks
- **Types**: `frontend/src/types/` - Shared TypeScript types

### Management Service

- **Routes**: `services/management-service/app/api/routes/` - REST endpoints (users, projects, sprints, backlog_items)
- **Models**: `services/management-service/app/models.py` - SQLModel database models
- **Schemas**: `services/management-service/app/schemas.py` - Pydantic request/response schemas
- **Security**: `services/management-service/app/core/security.py` - JWT auth, password hashing
- **Config**: `services/management-service/app/core/config.py` - Environment-based settings
- **Migrations**: `services/management-service/alembic/versions/` - Database migrations

### AI Agent Service

- **WebSocket**: `services/ai-agent-service/app/api/routes/chat_ws.py` - WebSocket chat implementation
- **Agent Execution**: `services/ai-agent-service/app/api/routes/agent_execution.py` - REST API for agent runs
- **PO Agent**: `services/ai-agent-service/app/agents/product_owner/` - Main orchestrator and sub-agents
- **Models**: `services/ai-agent-service/app/models.py` - Message and Agent models
- **Config**: `services/ai-agent-service/app/core/config.py` - OpenAI/Anthropic/LangFuse settings

## Testing WebSocket Integration

Manual testing using test files in root:

1. **HTML Client**: Open `test_websocket.html` in browser
2. **Python Script**: `python test_websocket.py`
3. **Step-by-step Guide**: Follow `TEST_WEBSOCKET_STEPS.md`

Automated E2E tests use Playwright (frontend/tests/).

## Environment Configuration

Required environment variables:

```bash
# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=vibesdlc

# Security
SECRET_KEY=your-secret-key-min-32-chars
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=adminpassword

# AI Services
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# LangFuse (optional observability)
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Kafka (external)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# CORS (development)
FRONTEND_HOST=http://localhost:5173
```

## Code Style & Conventions

### Python (Backend Services)

- **Formatting**: `ruff format` (services/management-service/scripts/format.sh)
- **Linting**: `ruff check` + `mypy` for type checking
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Async**: Use async/await for all route handlers and database operations
- **Type Hints**: Required for all functions (enforced by mypy)

### TypeScript/React (Frontend)

- **Linting**: Biome (`npm run lint`)
- **Type Checking**: tsc (`npm run typecheck`)
- **Naming**: PascalCase for components/files (UserCard.tsx), camelCase for functions/variables
- **File Routing**: TanStack Router uses file structure (routes/workspace/$workspaceId.tsx)
- **State Management**: TanStack Query for server state, local state for UI

### Testing

- **Python**: pytest with coverage reports, tests in `tests/` directories
- **Frontend**: Playwright for E2E, tests in `frontend/tests/`
- **Naming**: Python `test_*.py`, TypeScript `*.spec.ts`

### Commits

Follow Conventional Commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance
- `test:` - Testing
- `docs:` - Documentation

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
from app.core.database import get_session

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

## Documentation References

- `README.md` - Project overview, deployment modes
- `AGENTS.md` - Repository guidelines, commands, coding style
- `WEBSOCKET_IMPLEMENTATION_SUMMARY.md` - Complete WebSocket implementation details
- `docs/WEBSOCKET_CHAT.md` - WebSocket protocol specification
- `docs/AGENT_INTEGRATION.md` - Agent integration guide
- `frontend/README.md` - Frontend-specific setup and development
