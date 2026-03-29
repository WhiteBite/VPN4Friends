"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, api_client: AsyncClient):
        """Test health check endpoint."""
        response = await api_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_ready_check(self, api_client: AsyncClient):
        """Test ready check endpoint."""
        response = await api_client.get("/api/ready")

        assert response.status_code == 200


class TestUserEndpoints:
    """Tests for user endpoints."""

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, api_client: AsyncClient):
        """Test getting user profile without auth."""
        response = await api_client.get("/api/me")

        # The backend requires WebApp InitData header. Without it:
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_create_vpn_request(self, api_client: AsyncClient):
        """Test requesting VPN."""
        response = await api_client.post("/api/me/request")

        # Should return auth error
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_get_vpn_links_unauthorized(self, api_client: AsyncClient):
        """Test getting VPN links without auth."""
        response = await api_client.get("/api/me/link")
        assert response.status_code in [401, 422]


class TestAdminEndpoints:
    """Tests for admin endpoints."""

    @pytest.mark.asyncio
    async def test_get_pending_requests_unauthorized(self, api_client: AsyncClient):
        """Test getting pending requests without admin auth."""
        response = await api_client.get("/api/staff/requests")

        # Should return 401 Unauthorized because missing InitData
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_approve_request_unauthorized(self, api_client: AsyncClient):
        """Test approving request without admin auth."""
        response = await api_client.post("/api/staff/requests/1/approve")

        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_reject_request_unauthorized(self, api_client: AsyncClient):
        """Test rejecting request without admin auth."""
        response = await api_client.post("/api/staff/requests/1/reject")

        assert response.status_code in [401, 422]
