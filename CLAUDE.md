# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibeSDLC is a Software Development Lifecycle Multi-agent System implementing Lean Kanban methodology with AI agents. The system consists of a FastAPI backend (Python 3.13) and a React + TypeScript frontend (Vite).

**Architecture Pattern**: Monorepo with separate backend and frontend directories, sharing no code between them.

## Development Commands

### Backend (Python/FastAPI)

```bash
# Navigate to backend
cd backend

# Install dependencies (using uv)
uv pip install -e .

# Run development server (with auto-reload)
python main.py
# OR
uvicorn main:app --host localhost --port 8000 --reload

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Check user data (utility script)
python check_user.py
```

### Frontend (React/TypeScript/Vite)

```bash
# Navigate to frontend
cd frontend

# Install dependencies (using pnpm)
pnpm install

# Development server (typically runs on port 5176)
pnpm dev

# Build for production
pnpm build

# Preview production build
pnpm preview

# Lint
pnpm lint
```

## Backend Architecture

### Core Structure

- **`main.py`**: FastAPI application entry point with CORS middleware, lifespan management, and router registration
- **`app/database.py`**: SQLAlchemy async engine configuration with PostgreSQL+asyncpg
  - **Important**: Database URL is hardcoded in `database.py` (should use environment variable)
- **`app/models.py`**: SQLAlchemy ORM models for all entities (User, RefreshToken, Project, Epic, Story, Agent, etc.)
- **`app/enums.py`**: Enums for StoryStatus, StoryType, StoryPriority, AgentType
- **`app/schemas.py`**: Pydantic schemas for authentication/user operations
- **`app/kanban_schemas.py`**: Pydantic schemas for Kanban entities (Project, Epic, Story, Agent, TechStack, Metrics)
- **`app/dependencies.py`**: FastAPI dependencies for authentication and authorization (JWT token validation, user retrieval, ownership verification)
- **`app/core/security.py`**: JWT token creation/validation, password hashing
- **`app/core/config.py`**: Configuration settings

### Service Layer Pattern

All business logic is in `app/services/`:
- `auth_service.py`: Authentication, registration, token management, device fingerprinting
- `user_service.py`: User CRUD operations
- `tech_stack_service.py`: Technology stack management
- `agent_service.py`: AI agent management with workload tracking
- `project_service.py`: Project CRUD with Kanban board configuration (WIP limits, columns)
- `epic_service.py`: Epic management with progress tracking
- `story_service.py`: Story management with status transitions, assignments, WIP limit validation
- `metrics_service.py`: Lean Kanban metrics (throughput, cycle time, lead time, CFD)

### API Routers

Located in `app/routers/`, each router corresponds to a service:
- `auth.py`: POST /auth/register, /auth/login, /auth/refresh, /auth/logout
- `users.py`: GET /users/me
- `tech_stacks.py`: CRUD for tech stacks
- `agents.py`: CRUD for AI agents
- `projects.py`: CRUD for projects with Kanban configuration
- `epics.py`: CRUD for epics
- `stories.py`: CRUD for stories with full Kanban workflow
- `metrics.py`: GET endpoints for metrics and analytics

### Database Migrations

- Uses Alembic for migrations
- Migration files in `backend/alembic/Versions/`
- Automatic table creation on startup via `lifespan` in `main.py`

### Authentication & Security

- JWT-based authentication with access tokens (short-lived) and refresh tokens (long-lived)
- Refresh tokens stored in database with hashing, device fingerprinting, IP tracking
- Bearer token scheme for protected routes
- CSRF protection consideration (headers: X-CSRF-Token, X-Device-Fingerprint)
- Role-based access: Only project owners can modify their projects/epics/stories

## Frontend Architecture

### Tech Stack

- **React 19** with TypeScript
- **Vite** for bundling and dev server
- **React Router v7** for routing
- **Tailwind CSS** + **Radix UI** for styling
- **shadcn/ui** components (configured in `components.json`)
- **React Hook Form** + **Zod** for form validation
- **Axios** for API requests
- **i18next** for internationalization (Vietnamese + English support)
- **Sonner** for toast notifications
- **FingerprintJS** for device fingerprinting

### Core Structure

- **`src/App.tsx`**: Main app component with routing, lazy-loaded routes, AuthProvider
- **`src/main.tsx`**: Application entry point
- **`src/core/`**: Core application logic
  - `contexts/`: React contexts (e.g., AuthContext)
  - `constants/`: Constants like route definitions
  - `lib/`: Core libraries
  - `utils/`: Utility functions
- **`src/features/`**: Feature-based organization
  - `auth/`: Authentication pages (LoginPage, RegisterPage)
  - `dashboard/`: Dashboard components
  - `projects/`: Project management pages (ProjectsPage)
  - `metrics/`: Metrics visualization
- **`src/pages/`**: Top-level page components (DashboardPage, HomePage)
- **`src/shared/`**: Shared/reusable components
  - `components/`: RouteGuards (ProtectedRoute, PublicRoute), LoadingSpinner
  - `layouts/`: AppLayout
- **`src/components/`**: shadcn/ui components
- **`src/lib/utils.ts`**: Utility functions (e.g., `cn` for className merging)
- **`src/locales/`**: i18n translation files (vi/common.json, vi/auth.json)

### Routing

Routes defined in `src/core/constants/routes.ts` and used in `App.tsx`:
- Public routes: `/login`, `/register` (wrapped in `PublicRoute`)
- Protected routes: `/`, `/dashboard`, `/projects` (wrapped in `ProtectedRoute` + `AppLayout`)
- Route guards redirect authenticated users away from login/register and unauthenticated users to login

### State Management

- React Context for global state (AuthContext for authentication)
- Local component state with hooks
- No global state library like Redux/Zustand (consider adding if complexity grows)

### API Integration

- Axios client likely configured in `src/core/lib/` or similar
- API base URL from environment variable (see `.env.example`)
- Authentication headers (Bearer token) set via interceptors

## Key Domain Concepts

### Kanban Workflow

The system implements Lean Kanban with these entities:
1. **Project**: Top-level container with Kanban board configuration (WIP limits, custom columns)
2. **TechStack**: Technologies used in a project
3. **Agent**: AI agents (FlowManager, BusinessAnalyst, Developer, Tester) with workload tracking
4. **Epic**: Large feature or initiative within a project
5. **Story**: Work item with status workflow (TODO → IN_PROGRESS → REVIEW → TESTING → DONE), type (UserStory/EnablerStory), priority, assignments to agents
6. **Metrics**: Throughput, cycle time, lead time, Cumulative Flow Diagram (CFD)

### Story Status Transitions

Stories follow a strict workflow with WIP limit validation:
- TODO → IN_PROGRESS → REVIEW → TESTING → DONE
- BLOCKED status available at any stage
- ARCHIVED for soft deletion
- WIP limits enforced per column when transitioning

### Agent Workload

Agents have capacity limits and current workload tracking:
- Stories can be assigned to agents
- System tracks active assignments
- Workload queries available for load balancing

## Development Patterns

### Backend

- Async/await throughout (SQLAlchemy async sessions, FastAPI async routes)
- Repository pattern via services (routers → services → database)
- Soft deletes: `deleted_at` field for Projects, Epics, Stories (filter with `deleted_at == None`)
- Relationship loading: `lazy="selectin"` on most relationships
- Error handling: HTTPException with appropriate status codes
- Authorization: Dependencies chain `get_current_user` → `get_current_active_user` → ownership verification

### Frontend

- Feature-based folder structure (group by feature, not by file type)
- Component composition with Radix UI primitives
- Form handling: React Hook Form + Zod schemas
- Code splitting: Lazy-loaded routes with `React.lazy()` and `Suspense`
- Styling: Tailwind utility classes + CSS variables for theming
- Type safety: TypeScript strict mode, interfaces/types for API responses

## Important Notes

1. **Database Configuration**: The database URL in `backend/app/database.py:10` is hardcoded. Consider moving to environment variable using `python-dotenv` and reading from `.env`.

2. **CORS**: Backend CORS is configured for multiple localhost ports (5173-5176) to support multiple Vite dev server instances.

3. **No Tests**: The repository currently has no test files. Consider adding:
   - Backend: `pytest` + `pytest-asyncio` for async tests
   - Frontend: Vitest (already compatible with Vite) + React Testing Library

4. **Migration Strategy**: Alembic migrations exist but auto-creation on startup (`main.py:16`) might conflict. Choose one approach: either migrations OR auto-creation, not both.

5. **CrewAI Integration**: `pyproject.toml` includes `crewai` and `crewai-tools` dependencies, suggesting multi-agent orchestration, but usage is not immediately visible in the codebase.

6. **Frontend Environment**: The frontend `.env` file should contain `VITE_API_URL` pointing to the backend (e.g., `http://localhost:8000`).

7. **i18n**: The app supports Vietnamese and English. Add translations to `src/locales/{language}/` JSON files.

## Common Workflows

### Adding a New API Endpoint

1. Define Pydantic schemas in `app/schemas.py` or `app/kanban_schemas.py`
2. Add business logic to appropriate service in `app/services/`
3. Create router endpoint in `app/routers/`
4. Register router in `main.py` if new router file
5. Add database migration if model changes: `alembic revision --autogenerate -m "description"`

### Adding a New Frontend Page

1. Create page component in `src/features/{feature}/pages/` or `src/pages/`
2. Define route constant in `src/core/constants/routes.ts`
3. Add lazy import in `src/App.tsx`
4. Add `<Route>` in `App.tsx` with appropriate route guard
5. Add navigation link in `AppLayout` or relevant component

### Modifying Database Schema

1. Update SQLAlchemy model in `app/models.py`
2. Update Pydantic schemas in `app/schemas.py` or `app/kanban_schemas.py`
3. Generate migration: `cd backend && alembic revision --autogenerate -m "description"`
4. Review generated migration in `alembic/Versions/`
5. Apply migration: `alembic upgrade head`
6. Update service layer and routers if needed
