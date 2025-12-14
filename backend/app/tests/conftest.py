"""Pytest configuration for auth tests - mocks environment variables"""
import os
import sys
from pathlib import Path

# Set environment variables BEFORE importing app modules
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("FIRST_SUPERUSER", "admin@test.com")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "testpass123")
os.environ.setdefault("SECRET_KEY", "testsecretkey123456789012345678901234567890")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("FRONTEND_HOST", "http://localhost:3000")

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))
