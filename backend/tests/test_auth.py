import pytest
from httpx import AsyncClient


class TestAuth:
    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "newpassword123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "another@example.com",
                "password": "newpassword123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401
