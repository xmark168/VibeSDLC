# FastAPI Basic Application

A production-ready FastAPI application template with authentication, database integration, and modern Python development practices.

## 🚀 Features

- **FastAPI** - Modern, fast web framework for building APIs
- **Async/Await** - Full async support with SQLAlchemy and asyncpg
- **Authentication** - JWT-based authentication with refresh tokens
- **Database** - PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching** - Redis integration for caching and sessions
- **Validation** - Pydantic models for request/response validation
- **Testing** - Comprehensive test suite with pytest
- **Docker** - Multi-stage Docker build with docker-compose
- **Code Quality** - Black, isort, flake8, mypy for code formatting and linting
- **Documentation** - Auto-generated OpenAPI/Swagger documentation

## 📋 Requirements

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose (optional)

## 🛠️ Installation

### Option 1: Local Development

1. **Clone and setup**:
```bash
# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Install dependencies with uv (recommended)
pip install uv
uv sync

# Or with pip
pip install -e ".[dev]"
```

2. **Database setup**:
```bash
# Start PostgreSQL and Redis (with Docker)
docker-compose up -d db redis

# Or install locally and create database
createdb fastapi_db
```

3. **Run the application**:
```bash
# Development mode
uvicorn app.main:app --reload

# Or with uv
uv run uvicorn app.main:app --reload
```

### Option 2: Docker Development

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up --build

# Run with tools (includes pgAdmin)
docker-compose --profile tools up --build
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_main.py -v
```

## 📚 API Documentation

Once the application is running, visit:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 🔐 Authentication

The API uses JWT tokens for authentication:

1. **Register**: `POST /api/v1/users/`
2. **Login**: `POST /api/v1/auth/login`
3. **Use token**: Include `Authorization: Bearer <token>` header
4. **Refresh**: `POST /api/v1/auth/refresh`

Example:
```bash
# Register user
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword123",
    "confirm_password": "securepassword123"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

## 🏗️ Project Structure

```
app/
├── api/v1/           # API routes
│   ├── endpoints/    # Individual endpoint modules
│   └── router.py     # Main API router
├── core/             # Core functionality
│   ├── config.py     # Configuration settings
│   ├── database.py   # Database setup
│   └── exceptions.py # Custom exceptions
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # Business logic
└── main.py          # Application entry point

tests/               # Test suite
docker-compose.yml   # Docker services
Dockerfile          # Application container
pyproject.toml      # Dependencies and tools
```

## ⚙️ Configuration

Key environment variables:

```bash
# Application
ENVIRONMENT=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## 🚀 Deployment

### Docker Production

```bash
# Build production image
docker build -t fastapi-app .

# Run with production settings
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=your-prod-db-url \
  fastapi-app
```

### Health Checks

- **Basic**: `GET /health`
- **Detailed**: `GET /api/v1/health/detailed`
- **Kubernetes**: `GET /api/v1/health/ready` and `GET /api/v1/health/live`

## 🛠️ Development

### Code Quality

```bash
# Format code
black app tests
isort app tests

# Lint code
flake8 app tests
mypy app

# Run all checks
pre-commit run --all-files
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 📝 License

This project is licensed under the MIT License.
