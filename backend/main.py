from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import time
from app.database import engine, get_db
from app.models import Base
from app.routers import auth, users, tech_stacks, agents, projects, epics, stories, metrics

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events for FastAPI app
    """
    # Startup: Tạo tables (nếu chưa có)
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)  # Uncomment để drop all tables
        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created successfully")
    print("VibeSDLC Backend is running...")

    yield
    await engine.dispose()
    print("Shutting down...")

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)

# API Metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Health check endpoints with database connectivity verification and connection pool monitoring",
    },
    {
        "name": "Authentication",
        "description": "Authentication endpoints: đăng ký, đăng nhập, refresh token, logout",
    },
    {
        "name": "Users",
        "description": "User management endpoints (yêu cầu authentication)",
    },
    {
        "name": "Tech Stacks",
        "description": "Technology stack management for project configuration",
    },
    {
        "name": "Agents",
        "description": "AI agent management with workload tracking",
    },
    {
        "name": "Projects",
        "description": "Project management with Lean Kanban board configuration",
    },
    {
        "name": "Epics",
        "description": "Epic management with progress tracking",
    },
    {
        "name": "Stories",
        "description": "Story management with full Kanban workflow (WIP limits, status transitions, agent assignments)",
    },
    {
        "name": "Metrics",
        "description": "Lean Kanban metrics and analytics (throughput, cycle time, lead time, CFD)",
    },
]

# Khởi tạo FastAPI app
app = FastAPI(
    title="VibeSDLC API",
    description="""
## VibeSDLC - Software Development Lifecycle Multi-agent System
    """,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "VibeSDLC Team",
        "url": "https://github.com/xmark168/VibeSDLC",
        "email": "support@vibesdlc.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    terms_of_service="https://vibesdlc.com/terms",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)

# Kanban system routers
app.include_router(tech_stacks.router)
app.include_router(agents.router)
app.include_router(projects.router)
app.include_router(epics.router)
app.include_router(stories.router)
app.include_router(metrics.router)

# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "message": "VibeSDLC API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint with actual database connectivity verification

    This endpoint verifies:
    - API service is running
    - Database connection is working
    - Response time measurement
    """
    start_time = time.time()

    try:
        # Verify database connectivity with a simple query
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        database_status = "connected"
        database_healthy = True
    except Exception as e:
        database_status = f"error: {str(e)}"
        database_healthy = False

    response_time = round((time.time() - start_time) * 1000, 2)  # milliseconds

    # Overall health status
    overall_status = "healthy" if database_healthy else "unhealthy"

    return {
        "status": overall_status,
        "database": {
            "status": database_status,
            "healthy": database_healthy
        },
        "response_time_ms": response_time,
        "version": "1.0.0"
    }

@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with database connection pool metrics

    Provides comprehensive health information including:
    - Database connectivity
    - Connection pool statistics
    - Query performance
    """
    start_time = time.time()
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }

    # Database connectivity check
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        health_data["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }

    # Connection pool statistics
    try:
        pool = engine.pool
        health_data["checks"]["connection_pool"] = {
            "status": "healthy",
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": engine.pool._max_overflow if hasattr(pool, '_max_overflow') else "N/A"
        }

        # Warn if pool is nearly exhausted
        if pool.checkedout() > pool.size() * 0.8:
            health_data["checks"]["connection_pool"]["warning"] = "Connection pool usage is high"
    except Exception as e:
        health_data["checks"]["connection_pool"] = {
            "status": "error",
            "message": f"Failed to get pool stats: {str(e)}"
        }

    # Database query performance test
    try:
        query_start = time.time()
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        result.scalar()
        query_time = round((time.time() - query_start) * 1000, 2)

        health_data["checks"]["database_performance"] = {
            "status": "healthy",
            "query_time_ms": query_time
        }

        if query_time > 1000:  # Warn if query takes more than 1 second
            health_data["checks"]["database_performance"]["warning"] = "Database queries are slow"
    except Exception as e:
        health_data["checks"]["database_performance"] = {
            "status": "error",
            "message": f"Performance check failed: {str(e)}"
        }

    health_data["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

    return health_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True
    )
