import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.main import api_router
from app.core.config import settings
from app.core.db import init_db, engine
from sqlmodel import Session


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database, create superuser
    with Session(engine) as session:
        init_db(session)

    # Start Kafka producer
    from app.crews.events.kafka_producer import get_kafka_producer, shutdown_kafka_producer
    try:
        producer = await get_kafka_producer()
        print("✓ Kafka producer started")
    except Exception as e:
        print(f"⚠️  Failed to start Kafka producer: {e}")
        print("   Continuing without Kafka support...")

    # Start all Kafka consumers
    from app.kafka.consumer_registry import start_all_consumers, shutdown_all_consumers
    try:
        await start_all_consumers()
        print("✓ All Kafka consumers started")
    except Exception as e:
        print(f"⚠️  Failed to start Kafka consumers: {e}")
        print("   Continuing without consumer support...")

    yield

    # Shutdown: cleanup consumers and producer
    print("Shutting down...")

    try:
        await shutdown_all_consumers()
        print("✓ Kafka consumers shut down")
    except Exception as e:
        print(f"Error shutting down consumers: {e}")

    try:
        await shutdown_kafka_producer()
        print("✓ Kafka producer shut down")
    except Exception as e:
        print(f"Error shutting down producer: {e}")

    print("✓ Application shutdown complete")


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
