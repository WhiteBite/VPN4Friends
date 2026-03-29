"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, api_client: AsyncClient):
        """Test health check endpoint returns OK."""
        response = await api_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_ready_check(self, api_client: AsyncClient):
        """Test readiness check endpoint returns ready."""
        response = await api_client.get("/api/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True


class TestEndpointsEndpoint:
    """Tests for /endpoints endpoint."""

    @pytest.mark.asyncio
    async def test_list_endpoints_empty(self, api_client: AsyncClient):
        """Test listing endpoints when none configured."""
        response = await api_client.get("/api/endpoints")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # May have endpoints if configured in test settings


class TestProtocolsEndpoint:
    """Tests for /protocols endpoint."""

    @pytest.mark.asyncio
    async def test_list_protocols(self, api_client: AsyncClient):
        """Test listing available protocols."""
        response = await api_client.get("/api/protocols")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Each protocol should have required fields
        for protocol in data:
            assert "name" in protocol
            assert "label" in protocol
            assert "description" in protocol
            assert "recommended" in protocol


class TestMeEndpoint:
    """Tests for /me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, api_client: AsyncClient):
        """Test getting user profile without Telegram auth."""
        # Without proper Telegram or Token auth, returns 401 Unauthorized
        response = await api_client.get("/api/me")

        # 401 = unauthorized (missing/invalid auth credentials)
        assert response.status_code == 401


class TestPresetsEndpoints:
    """Tests for /presets endpoints."""

    @pytest.mark.asyncio
    async def test_list_presets_unauthorized(self, api_client: AsyncClient):
        """Test listing presets without auth."""
        response = await api_client.get("/api/presets")

        # 401 = unauthorized (missing/invalid auth credentials)
        assert response.status_code == 401


class TestAPIRoot:
    """Tests for API root endpoint."""

    @pytest.mark.asyncio
    async def test_api_root(self, api_client: AsyncClient):
        """Test API root (may be 200 if frontend is built, or 404 if not)."""
        response = await api_client.get("/")

        # Root path (/) may serve MiniApp (200) or be unconfigured in CI (404)
        assert response.status_code in (200, 404)


class TestOpenAPISchema:
    """Tests for OpenAPI schema endpoints."""

    @pytest.mark.asyncio
    async def test_openapi_json(self, api_client: AsyncClient):
        """Test OpenAPI schema is available."""
        response = await api_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    @pytest.mark.asyncio
    async def test_docs_available(self, api_client: AsyncClient):
        """Test Swagger docs are available."""
        response = await api_client.get("/docs")

        assert response.status_code == 200
        assert "Swagger UI" in response.text or "Redoc" in response.text
