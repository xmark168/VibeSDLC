from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import engine
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
        "description": "Health check endpoints để kiểm tra trạng thái server và database",
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
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True
    )
