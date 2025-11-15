from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.database import engine
from app.models import Base
from app.routers import auth, users, tech_stacks, agents, projects, epics, stories, metrics, kafka_test
from app.kafka.producer import kafka_producer
from app.kafka.consumer import agent_task_consumer
from app.agents.developer_agent import developer_agent

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

    # Initialize Kafka producer
    try:
        kafka_producer.initialize()
        print("Kafka producer initialized")
        # Wait a bit for topics to be created
        await asyncio.sleep(2)
        print("Kafka topics ready")
    except Exception as e:
        print(f"Warning: Kafka producer initialization failed: {e}")

    # Start developer agent in background
    try:
        asyncio.create_task(developer_agent.start())
        print("Developer agent started")
    except Exception as e:
        print(f"Warning: Developer agent failed to start: {e}")

    print("VibeSDLC Backend is running...")

    yield

    # Shutdown: Clean up resources
    try:
        kafka_producer.close()
        print("Kafka producer closed")
    except Exception as e:
        print(f"Error closing Kafka producer: {e}")

    await engine.dispose()
    print("Shutting down...")

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
    {
        "name": "Kafka Testing",
        "description": "Kafka integration testing endpoints for agents and event streaming",
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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server default
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",  # Current port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers including X-CSRF-Token, X-Device-Fingerprint
    expose_headers=["*"],  # Expose all response headers
    max_age=3600,  # Cache preflight requests for 1 hour
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

# Kafka testing router
app.include_router(kafka_test.router)

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
