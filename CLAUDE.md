# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibeSDLC is a microservices-based Software Development Life Cycle (SDLC) platform that implements Scrum methodology using AI agents. The system features a peer-to-peer architecture where services communicate through external PostgreSQL and Kafka infrastructure, with no direct service dependencies.

## Core Architecture

### Service Structure
- **Management Service** (Port 8000): FastAPI backend with PostgreSQL for core business logic, user management, and authentication
- **AI Agent Service** (Port 8001): FastAPI service for AI operations using LangChain/LangGraph, integrating OpenAI & Anthropic Claude
- **Frontend** (Port 5173): React 19 + TypeScript with Vite, using Radix UI components and TailwindCSS

### Key Technologies
- **Backend**: Python 3.13+, FastAPI, SQLModel, Alembic for migrations
- **AI Framework**: LangChain 0.3+, LangGraph 0.6.7+, DeepAgents
- **Frontend**: React 19, TypeScript, Vite, TanStack Router & Query
- **Infrastructure**: Docker, PostgreSQL, Kafka (external), LangFuse (observability)

## Development Commands

### Primary Development Workflow
```bash
# Local development with included PostgreSQL
npm run dev              # Start all services with local PostgreSQL
npm run dev:build        # Build and start with local PostgreSQL
npm run dev:down         # Stop local development

# Production mode (requires external infrastructure)
npm run prod             # Start production mode
npm run prod:build       # Build and start production
npm run prod:down        # Stop production

# Monitoring and debugging
npm run logs             # View all service logs
npm run logs:management  # Management service logs only
npm run logs:ai          # AI agent service logs only
npm run logs:frontend    # Frontend logs only
npm run status           # Check service status
npm run clean            # Stop and remove everything
```

### Individual Service Development
```bash
# Frontend (requires Node.js 24+)
cd frontend
npm install
npm run dev              # Development server
npm run build            # Production build
npm run typecheck        # TypeScript validation
npm run lint             # Biome linting with auto-fix
npm run test:e2e         # Playwright end-to-end tests
npm run generate-client  # Generate API client from OpenAPI

# Backend services use uv/pip with pyproject.toml
cd services/management-service
uv sync                  # Install dependencies
pytest                   # Run tests
mypy app/                # Type checking
ruff check               # Linting

# Database migrations (Management Service)
docker-compose exec management-service alembic upgrade head
docker-compose exec management-service alembic revision --autogenerate -m "description"
```

### Testing Commands
```bash
# Frontend testing
cd frontend
npm run test:e2e         # Playwright E2E tests
npm run test:e2e:ui      # Playwright with UI

# Backend testing
docker-compose exec management-service pytest tests/unit/ -v --cov=app
docker-compose exec ai-agent-service pytest tests/ -v
```

## Agent Architecture

The AI Agent Service implements a sophisticated Scrum-based agent system with clearly defined roles:

### Agent Roles
- **Product Owner Agent**: Requirements clarification, backlog management, acceptance criteria
- **Scrum Master Agent**: Sprint planning, daily scrum facilitation, impediment tracking
- **Developer Agent**: Task implementation, pull requests, unit testing, code quality
- **Tester Agent**: Test generation, validation, defect reporting

### Agent Communication
- **LangGraph Workflows**: State-driven workflows for Scrum ceremonies (Sprint Planning, Daily Scrum, Sprint Review, Retrospective)
- **Kafka Integration**: Event-driven communication between agents
- **PostgreSQL State**: Persistent workflow state using langgraph-checkpoint-postgres
- **LangFuse Observability**: Comprehensive monitoring and tracing of agent interactions

### Developer Agent Workflow
The Developer Agent follows a structured 4-phase approach:
1. **Task Assignment & Analysis**: Receive from Scrum Master, analyze requirements, break down complex tasks
2. **Implementation & Testing**: Write production code, create unit tests (80%+ coverage), run local validation
3. **Code Submission & Review**: Commit with conventional format, create PR, trigger CI/CD pipeline
4. **Review & Integration**: Handle CI results, address feedback, merge to main, notify Tester Agent

## Code Quality Standards

### Python Services
- **Python 3.13+** required
- **Type hints** mandatory (mypy strict mode)
- **Test coverage** minimum 80%
- **Ruff** for linting with pyupgrade, flake8-bugbear
- **Conventional commits** format
- **Alembic** for database migrations

### Frontend Standards
- **TypeScript strict mode**
- **Biome** for linting and formatting
- **Playwright** for E2E testing
- **TanStack** patterns for data fetching and routing

### Agent Development Patterns
- **LangChain 0.3+** for enhanced model capabilities
- **Structured outputs** for reliable agent responses
- **LCEL** (LangChain Expression Language) for chain composition
- **State management** for workflow persistence across agent interactions
- **Error handling** and retry mechanisms in workflows
- **Conditional edges** for dynamic workflow routing

## Environment Configuration

### Local Development (.env)
```bash
# Local infrastructure (defaults work)
POSTGRES_SERVER=localhost
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Required AI API keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Optional observability
LANGFUSE_SECRET_KEY=your-langfuse-secret
LANGFUSE_PUBLIC_KEY=your-langfuse-public
LANGFUSE_HOST=your-langfuse-host
```

### Production Configuration
Requires external PostgreSQL and Kafka infrastructure. Update environment variables to point to external services.

## Database Operations

### Management Service Database
```bash
# Run migrations
docker-compose exec management-service alembic upgrade head

# Create new migration
docker-compose exec management-service alembic revision --autogenerate -m "add new table"

# Access database directly
docker-compose exec postgres psql -U postgres -d app
```

### AI Agent State Persistence
The AI agents use PostgreSQL for LangGraph state persistence via `langgraph-checkpoint-postgres`. State is automatically managed through the workflow engine.

## Integration Patterns

### Kafka Event Streaming
- **Topics**: user-events, ai-requests, ai-responses
- **Pattern**: Agents communicate through Kafka events for loose coupling
- **Configuration**: External Kafka cluster (not containerized)

### API Integration
- **Management API**: http://localhost:8000/docs
- **AI Agent API**: http://localhost:8001/docs
- **Frontend**: Communicates with both APIs via generated TypeScript client

## Common Development Tasks

### Adding a New Agent
1. Create agent module in `services/ai-agent-service/app/agents/`
2. Define agent state and workflow using LangGraph
3. Implement tool integrations and memory management
4. Add Kafka event handlers for inter-agent communication
5. Register agent in the main FastAPI application

### Modifying Scrum Workflows
1. Update workflow definitions in relevant agent directories
2. Modify state schemas if needed
3. Update conditional edges for new workflow paths
4. Test workflow changes using the agent testing patterns
5. Update LangFuse observability if adding new events

### Database Schema Changes
1. Modify SQLModel models in management service
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration for correctness
4. Apply migration: `alembic upgrade head`
5. Update API schemas and endpoints accordingly

## Troubleshooting

### Common Issues
- **Kafka Connection Failed**: Verify external Kafka accessibility and topic creation
- **Database Connection Issues**: Check PostgreSQL container status and environment variables
- **Frontend Build Issues**: Clear node_modules and reinstall dependencies
- **Agent State Issues**: Check PostgreSQL checkpoint tables and LangGraph configuration

### Port Conflicts
Default ports: Frontend (5173), Management (8000), AI Agent (8001), PostgreSQL (5432)
Use `lsof -i :PORT` to identify conflicts.

### Agent Debugging
- Use LangFuse dashboard for workflow observability
- Check Kafka topic messages for inter-agent communication
- Review PostgreSQL checkpoint tables for workflow state
- Enable debug logging in FastAPI applications