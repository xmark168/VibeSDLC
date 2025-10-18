"""
Tests for main application functionality.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self):
        """Test basic health check endpoint."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    @pytest.mark.asyncio
    async def test_health_check_async(self):
        """Test health check with async client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAPIRoutes:
    """Test API route structure."""

    def test_api_health_endpoint(self):
        """Test API health endpoint."""
        client = TestClient(app)
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_openapi_docs_available_in_dev(self):
        """Test that OpenAPI docs are available in development."""
        client = TestClient(app)
        response = client.get("/api/v1/docs")

        # Should be available in development environment
        assert response.status_code == 200

    def test_cors_headers(self):
        """Test CORS headers are present."""
        client = TestClient(app)
        response = client.options("/api/v1/health/")

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Test error handling."""

    def test_404_error(self):
        """Test 404 error handling."""
        client = TestClient(app)
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test method not allowed error."""
        client = TestClient(app)
        response = client.post("/health")

        assert response.status_code == 405
