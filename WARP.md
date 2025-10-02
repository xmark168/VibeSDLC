# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

VibeSDLC is a microservices platform built for intelligent task management. The architecture is **peer-to-peer** with no service dependencies - all services connect directly to external infrastructure (PostgreSQL, Kafka).

### Key Components
- **Management Service** (FastAPI): Core business logic, user management, authentication
- **AI Agent Service** (FastAPI): LangGraph-powered AI task analysis with multi-LLM support
- **Frontend** (React + TypeScript): Modern UI with file-based routing

### External Dependencies
- **PostgreSQL**: Primary database (external in production, local for development)
- **Kafka**: Event-driven communication (self-hosted externally)
- **LLM APIs**: OpenAI, Anthropic Claude (optional)
- **LangFuse**: AI observability (optional)

## Common Development Commands

### Full Stack Operations
```bash
# Local development with included PostgreSQL
npm run dev              # Start all services with local DB
npm run dev:build        # Rebuild and start
npm run dev:down         # Stop development stack

# Production mode (requires external infrastructure)
npm run prod             # Start with external PostgreSQL/Kafka
npm run prod:build       # Rebuild and start production
npm run prod:down        # Stop production stack

# Monitoring
npm run logs             # View all service logs
npm run logs:management  # Management service only
npm run logs:ai          # AI agent service only
npm run logs:frontend    # Frontend only
npm run status           # Check service status

# Cleanup
npm run clean            # Stop and remove everything
```

### Frontend Development
```bash
cd frontend
npm install              # Install dependencies
npm run dev              # Start dev server (localhost:5173)
npm run build            # Production build
npm run lint             # Run Biome linter
npm run typecheck        # TypeScript checking
npm run test:e2e         # Run Playwright tests
npm run test:e2e:ui      # E2E tests with UI
npm run generate-client  # Generate API client from OpenAPI
npm run ci               # Full check pipeline
```

### Backend Service Development
```bash
# Management Service (Port 8000)
cd services/management-service
# Run tests
docker compose exec management-service pytest

# AI Agent Service (Port 8001) 
cd services/ai-agent-service
# Run tests
docker compose exec ai-agent-service pytest

# Database migrations (Management Service)
docker compose exec management-service alembic upgrade head
```

### Testing Commands
```bash
# Frontend E2E testing
cd frontend
npm run test:e2e         # Run all E2E tests
npm run test:e2e:ui      # Interactive test runner

# Backend testing
docker compose exec management-service pytest
docker compose exec ai-agent-service pytest

# Health checks
curl http://localhost:8000/health  # Management service
curl http://localhost:8001/health  # AI agent service
```

## Architecture Understanding

### Service Communication Pattern
- **Event-Driven**: Services communicate via Kafka topics (user-events, item-events, ai-requests, ai-responses)
- **Peer-to-Peer**: No service dependencies - each connects directly to PostgreSQL and Kafka
- **API Integration**: Frontend communicates with both services via REST APIs

### AI Agent Architecture
The AI Agent Service uses **LangGraph** for complex workflows:
1. **Task Analysis**: LLM analyzes complexity and requirements
2. **Suggestion Generation**: Creates actionable recommendations  
3. **Prioritization**: Determines priority and next actions
4. **Event Processing**: Automatically processes new tasks via Kafka

### Frontend Architecture
- **File-based Routing**: TanStack Router with automatic code splitting
- **Server State**: TanStack Query for caching and API management
- **UI Components**: Chakra UI v3 with custom theme system
- **Type Safety**: Full TypeScript with auto-generated API client

### Database & State Management
- **PostgreSQL**: Single database shared by Management Service
- **Event Sourcing**: Kafka for cross-service communication
- **Authentication**: JWT tokens with 8-day expiration
- **Caching**: TanStack Query handles client-side caching

## Development Environment Setup

### Environment Variables
**Required for all modes:**
```env
SECRET_KEY=your-secret-key
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=your-password
```

**Local development (.env defaults work):**
```env
POSTGRES_SERVER=localhost
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

**Production (external infrastructure):**
```env
POSTGRES_SERVER=your-postgres-server
KAFKA_BOOTSTRAP_SERVERS=your-kafka-server:9092
POSTGRES_PASSWORD=your-secure-password
```

**AI features (optional):**
```env
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
LANGFUSE_SECRET_KEY=your-langfuse-secret
LANGFUSE_PUBLIC_KEY=your-langfuse-public
```

### Two Deployment Modes

**Local Development:**
- Uses `docker-compose.yml` + `docker-compose.local.yml`
- Includes PostgreSQL container
- Kafka must be external (localhost:9092)

**Production:**
- Uses `docker-compose.yml` only
- Requires external PostgreSQL and Kafka
- Services connect directly to external infrastructure

### Port Configuration
- **Frontend**: 5173
- **Management Service**: 8000 (API docs: /docs)
- **AI Agent Service**: 8001
- **PostgreSQL**: 5432 (local development only)

## Key Development Patterns

### Frontend Patterns
- **Route Components**: Minimal, use dynamic imports for large components
- **API Integration**: Use auto-generated client with TanStack Query
- **Form Handling**: React Hook Form with TypeScript validation
- **Error Handling**: React Error Boundary with custom toast system
- **State Management**: TanStack Query for server state, React state for UI

### Backend Patterns
- **SQLModel**: Database models with Pydantic validation
- **FastAPI**: Async endpoints with automatic OpenAPI generation
- **Event Publishing**: Kafka events on CRUD operations
- **Authentication**: JWT-based with dependency injection
- **Testing**: Pytest with database fixtures

### AI Agent Patterns
- **LangGraph Workflows**: State-based AI processing pipelines
- **Multi-LLM Support**: Anthropic primary, OpenAI fallback
- **Event Processing**: Automatic task analysis on creation
- **Observability**: LangFuse tracing for debugging

### Docker Development
- **Service Isolation**: Each service has its own Dockerfile
- **Volume Mounting**: Local development with hot reloading
- **Health Checks**: Built-in health endpoints for monitoring
- **Environment Override**: Local vs production configurations

## File Generation Notes

### API Client Generation
The frontend auto-generates API clients from OpenAPI specs:
```bash
cd frontend
npm run generate-client  # Updates src/client/
```

### Database Migrations
Management service uses Alembic for database schema:
```bash
# Inside management service
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### LangGraph Studio Integration
AI Agent Service includes LangGraph Studio configuration:
- `langgraph.json`: Studio configuration
- `studio_graph.py`: Entry point for visual debugging

## Common Troubleshooting

### Kafka Connection Issues
- Verify external Kafka is accessible from Docker containers
- Check `KAFKA_BOOTSTRAP_SERVERS` environment variable
- Ensure required topics exist or auto-create is enabled

### Database Connection Issues
- Local: Check PostgreSQL container health
- Production: Verify external PostgreSQL accessibility
- Check password and connection string configuration

### Frontend Build Issues
- Clear node_modules and reinstall if TypeScript errors persist  
- Regenerate API client if backend schema changes
- Run `npm run typecheck` to catch type issues early

### Service Communication
- Verify all services are healthy via `/health` endpoints
- Check Docker networking if services can't reach each other
- Monitor Kafka topics for event flow debugging