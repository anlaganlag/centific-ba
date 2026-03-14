"""
Tests for authentication API endpoints.

P0 Security: Ensure auth endpoints behave correctly.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Tests for /api/auth endpoints."""

    async def test_missing_token_returns_401(self):
        """Unauthorized access to protected endpoint should return 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/me")
            assert response.status_code == 401

    async def test_invalid_token_returns_401(self):
        """Invalid token should return 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer invalid_token"}
            )
            assert response.status_code == 401

    async def test_malformed_auth_header_returns_401(self):
        """Malformed authorization header should return 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Missing "Bearer" prefix
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "some_token"}
            )
            assert response.status_code == 401

    async def test_register_with_existing_email_returns_400(self):
        """Registering with existing email should return 400."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First registration
            await client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": "password123",
                "display_name": "Test User"
            })

            # Second registration with same email
            response = await client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": "password456",
                "display_name": "Another User"
            })
            assert response.status_code == 400
            assert "already registered" in response.json()["detail"].lower()

    async def test_login_with_wrong_password_returns_401(self):
        """Login with wrong password should return 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Register user
            await client.post("/api/auth/register", json={
                "email": "wrongpass@example.com",
                "password": "correct_password",
                "display_name": "Test User"
            })

            # Try to login with wrong password
            response = await client.post("/api/auth/login", json={
                "email": "wrongpass@example.com",
                "password": "wrong_password"
            })
            assert response.status_code == 401

    async def test_login_returns_valid_tokens(self):
        """Successful login should return access and refresh tokens."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Register user
            await client.post("/api/auth/register", json={
                "email": "tokens@example.com",
                "password": "password123",
                "display_name": "Test User"
            })

            # Login
            response = await client.post("/api/auth/login", json={
                "email": "tokens@example.com",
                "password": "password123"
            })

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
