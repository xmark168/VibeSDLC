<div align="center">
  <img src="./frontend/public/assets/images/logo.png" alt="VibeSDLC Logo" width="200"/>
  
  # VibeSDLC

  AI-powered Software Development Life Cycle (SDLC) platform with intelligent agents for automated development, testing, and business analysis.

  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev/)
  [![Apache Kafka](https://img.shields.io/badge/Kafka-7.5-231F20?logo=apache-kafka)](https://kafka.apache.org/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)](https://www.postgresql.org/)
</div>

---

## Overview

VibeSDLC is a comprehensive AI agent system that automates software development workflows. It provides specialized AI agents for different roles (Team Leader, Developer, Tester, Business Analyst) working collaboratively to deliver features from requirements to deployment.

## Architecture

```
VibeSDLC/
├── backend/          # FastAPI backend with AI agent orchestration
│   ├── app/
│   │   ├── agents/   # AI agent implementations (developer, tester, BA)
│   │   ├── api/      # REST API routes
│   │   ├── core/     # Core services, config, database
│   │   ├── kafka/    # Event streaming infrastructure
│   │   ├── models/   # Database models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   └── websocket/# Real-time communication
│   └── main.py       # Application entry point
├── frontend/         # React + Vite frontend
│   └── src/
└── docker-compose.yml
```

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI/ML**: LangChain, LangGraph, LiteLLM
- **Database**: PostgreSQL 16 + SQLModel
- **Message Queue**: Apache Kafka
- **Cache**: Redis
- **Vector DB**: Qdrant
- **Auth**: JWT with PyJWT
- **Monitoring**: Sentry, Langfuse

### Frontend
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Routing**: TanStack Router
- **State**: Zustand, TanStack Query
- **UI**: Radix UI + TailwindCSS
- **Real-time**: WebSocket, Server-Sent Events
- **Code Editor**: Monaco Editor
- **Markdown**: React Markdown with KaTeX

### Infrastructure
- Docker Compose
- Zookeeper + Kafka
- PostgreSQL with connection pooling
- Redis for caching

## Agent Architecture

### Agent Types

1. **Team Leader Agent** (`team_leader`)
   - Central coordinator and communication hub
   - Handles user interactions and delegates to specialists
   - Skills: conversation management, task delegation, team coordination
   - Acts as first point of contact for all user messages
   - Provides proactive greetings when specialists complete tasks

2. **Developer Agent** (`developer`)
   - Skills: frontend-component, api-route, database-model, authentication, state-management, debugging
   - Framework: Next.js 16, React 19, TypeScript
   - Generates production-ready code with best practices

3. **Tester Agent** (`tester`)
   - Skills: unit-test, integration-test
   - Testing frameworks: Jest, React Testing Library
   - Writes comprehensive test suites

4. **Business Analyst Agent** (`ba-agent`)
   - CRUD-based intent classification
   - Feature clarification and requirements analysis
   - Question handling for user stories

### Agent Workflow

```
User Message → Team Leader (Router)
                    ↓
        ┌───────────┼───────────┐
        ↓           ↓           ↓
    BA Agent    Developer    Tester
        ↓           ↓           ↓
   Requirements → Code → Tests → Review
        ↓           ↓           ↓
    Kafka Events → Checkpoints → WebSocket Updates
```

**Conversation Context Flow:**
- User messages without @mention → Active agent (7-15min timeout) or Team Leader
- @mention → Direct to mentioned agent (one-off, doesn't change context)
- Agent response → Sets that agent as active in conversation
- Task completion → Clears context, Team Leader sends proactive greeting

---

## Key Features

### AI Agent System
- **Multi-Agent Collaboration**: Team Leader coordinates Developer, Tester, and BA agents
- **LangGraph Orchestration**: State machine-based agent workflows
- **Checkpoint System**: Pause/resume agent execution with PostgreSQL checkpoints
- **Agent Pool Management**: Dynamic agent allocation and monitoring
- **Skills-based Architecture**: Modular agent capabilities (Next.js, testing, database, etc.)

### Development Automation
- Feature planning and decomposition
- Code generation (frontend components, API routes, database models)
- Authentication implementation (NextAuth v5)
- State management (Zustand)
- TypeScript type generation

### Testing Automation
- Unit tests (Jest + React Testing Library)
- Integration tests
- API route testing
- Mock generation

### Real-time Collaboration
- WebSocket connections for live updates
- Kafka event streaming
- Activity buffering and broadcasting
- Story state management

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js ≥24.0.0 (for frontend development)
- Python ≥3.11 (for backend development)

### Quick Start with Docker

```bash
# Clone the repository
git clone <repository-url>
cd VibeSDLC

# Start all services
docker compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/v1/docs
# Kafka UI: http://localhost:8080
```

### Backend Development Setup

```bash
cd backend

# Create virtual environment (recommended: uv)
pip install uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start development server
python dev.py
# or
uvicorn app.main:app --reload --port 8000
```

### Frontend Development Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Set up environment variables
cp .env.example .env

# Generate API client from OpenAPI spec
pnpm run generate-client

# Start development server
pnpm run dev
```

## Development Workflow

### Running Tests

**Backend:**
```bash
cd backend
pytest app/tests -v
# Unit tests only
pytest -m unit
# Integration tests only
pytest -m integration
```

**Frontend:**
```bash
cd frontend
pnpm run test:e2e
pnpm run test:e2e:ui
```

### Code Quality

**Backend:**
```bash
cd backend
# Format and lint
ruff check --fix .
ruff format .
```

**Frontend:**
```bash
cd frontend
# Type check
pnpm run typecheck
# Lint and format
pnpm run lint
# CI check (typecheck + lint + build)
pnpm run ci
```

### Database Migrations

```bash
cd backend
# Create new migration
alembic revision --autogenerate -m "Description"
# Apply migrations
alembic upgrade head
# Rollback
alembic downgrade -1
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | FastAPI application |
| Frontend | 5173 | Vite dev server |
| PostgreSQL | 5433 | Main database |
| Redis | 6379 | Cache and session store |
| Kafka | 9092 | Event streaming |
| Kafka UI | 8080 | Kafka management interface |
| Zookeeper | 2181 | Kafka coordination |

## Environment Variables

### Backend (.env)
```env
ENVIRONMENT=local
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=vibeuser
POSTGRES_PASSWORD=vibepass
POSTGRES_DB=vibedb

REDIS_HOST=localhost
REDIS_PORT=6379

KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# AI/LLM Configuration
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
TAVILY_API_KEY=your_key

# Optional
SENTRY_DSN=your_sentry_dsn
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_key
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
```

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

## Production Deployment

```bash
# Build and run production containers
docker compose -f docker-compose.prod.yml up -d

# Or with Kafka cluster
docker compose -f docker-compose.kafka.yml up -d
```

## Monitoring & Observability

- **Logging**: Structured logging with Python's logging module
- **Error Tracking**: Sentry integration
- **Agent Monitoring**: Built-in agent pool monitoring (30s interval)
- **Metrics**: Langfuse for LLM observability
- **Real-time**: WebSocket activity streams

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

