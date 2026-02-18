import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestAgents:
    @pytest.mark.asyncio
    async def test_create_agent(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/agents",
            json={
                "name": "Test Agent",
                "description": "A test agent",
                "agent_type": "openai",
                "config": {"model": "gpt-4"},
                "enabled": True
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Agent"
        assert data["agent_type"] == "openai"

    @pytest.mark.asyncio
    async def test_list_agents(self, client: AsyncClient, auth_headers: dict):
        # Create an agent first
        await client.post(
            "/api/agents",
            json={
                "name": "List Test Agent",
                "description": "A test agent for listing",
                "agent_type": "openai",
                "config": {},
                "enabled": True
            },
            headers=auth_headers
        )

        response = await client.get("/api/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_agent(self, client: AsyncClient, auth_headers: dict):
        # Create an agent first
        create_response = await client.post(
            "/api/agents",
            json={
                "name": "Get Test Agent",
                "description": "A test agent for getting",
                "agent_type": "openai",
                "config": {},
                "enabled": True
            },
            headers=auth_headers
        )
        agent_id = create_response.json()["id"]

        response = await client.get(f"/api/agents/{agent_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test Agent"

    @pytest.mark.asyncio
    async def test_update_agent(self, client: AsyncClient, auth_headers: dict):
        # Create an agent first
        create_response = await client.post(
            "/api/agents",
            json={
                "name": "Update Test Agent",
                "description": "A test agent for updating",
                "agent_type": "openai",
                "config": {},
                "enabled": True
            },
            headers=auth_headers
        )
        agent_id = create_response.json()["id"]

        response = await client.put(
            f"/api/agents/{agent_id}",
            json={"name": "Updated Agent Name"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Agent Name"

    @pytest.mark.asyncio
    async def test_delete_agent(self, client: AsyncClient, auth_headers: dict):
        # Create an agent first
        create_response = await client.post(
            "/api/agents",
            json={
                "name": "Delete Test Agent",
                "description": "A test agent for deleting",
                "agent_type": "openai",
                "config": {},
                "enabled": True
            },
            headers=auth_headers
        )
        agent_id = create_response.json()["id"]

        response = await client.delete(f"/api/agents/{agent_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(f"/api/agents/{agent_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_agent(self, client: AsyncClient, auth_headers: dict):
        # Create an agent first
        create_response = await client.post(
            "/api/agents",
            json={
                "name": "Toggle Test Agent",
                "description": "A test agent for toggling",
                "agent_type": "openai",
                "config": {},
                "enabled": True
            },
            headers=auth_headers
        )
        agent_id = create_response.json()["id"]

        # Disable
        response = await client.post(f"/api/agents/{agent_id}/disable", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["enabled"] is False

        # Enable
        response = await client.post(f"/api/agents/{agent_id}/enable", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["enabled"] is True
