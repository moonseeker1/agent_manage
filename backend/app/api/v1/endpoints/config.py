from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
import json

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.agent_service import AgentService, AgentGroupService

router = APIRouter(prefix="/config", tags=["Configuration"])


class ConfigExport(BaseModel):
    version: str = "1.0"
    agents: List[dict] = []
    groups: List[dict] = []


@router.get("/export")
async def export_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all agents and groups configuration"""
    agent_service = AgentService(db)
    group_service = AgentGroupService(db)

    # Get all agents
    agents, _ = await agent_service.get_agents(page=1, page_size=1000)
    agents_data = [
        {
            "name": a.name,
            "description": a.description,
            "agent_type": a.agent_type,
            "config": a.config,
            "enabled": a.enabled
        }
        for a in agents
    ]

    # Get all groups
    groups, _ = await group_service.get_groups(page=1, page_size=1000)
    groups_data = [
        {
            "name": g.name,
            "description": g.description,
            "execution_mode": g.execution_mode,
            "members": [
                {"agent_name": m.agent.name, "priority": m.priority}
                for m in g.members
            ]
        }
        for g in groups
    ]

    config = ConfigExport(
        agents=agents_data,
        groups=groups_data
    )

    return JSONResponse(
        content=config.model_dump(),
        headers={
            "Content-Disposition": "attachment; filename=agent_config.json"
        }
    )


@router.post("/import")
async def import_config(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import agents and groups from configuration file"""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    try:
        content = await file.read()
        config = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    agent_service = AgentService(db)
    group_service = AgentGroupService(db)

    results = {
        "agents_created": 0,
        "agents_skipped": 0,
        "groups_created": 0,
        "groups_skipped": 0,
        "errors": []
    }

    # Create agents
    created_agents = {}
    for agent_data in config.get("agents", []):
        try:
            from app.schemas.agent import AgentCreate
            agent_create = AgentCreate(**agent_data)
            agent = await agent_service.create_agent(agent_create)
            created_agents[agent_data["name"]] = agent.id
            results["agents_created"] += 1
        except Exception as e:
            results["agents_skipped"] += 1
            results["errors"].append(f"Agent '{agent_data.get('name')}': {str(e)}")

    # Create groups
    for group_data in config.get("groups", []):
        try:
            from app.schemas.agent import AgentGroupCreate

            # Map agent names to IDs
            agent_ids = []
            for member in group_data.get("members", []):
                agent_name = member.get("agent_name")
                if agent_name in created_agents:
                    agent_ids.append(str(created_agents[agent_name]))

            group_create = AgentGroupCreate(
                name=group_data["name"],
                description=group_data.get("description"),
                execution_mode=group_data.get("execution_mode", "sequential"),
                agent_ids=agent_ids
            )
            await group_service.create_group(group_create)
            results["groups_created"] += 1
        except Exception as e:
            results["groups_skipped"] += 1
            results["errors"].append(f"Group '{group_data.get('name')}': {str(e)}")

    return results


@router.post("/agents/batch-delete")
async def batch_delete_agents(
    agent_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete multiple agents"""
    from uuid import UUID

    agent_service = AgentService(db)
    deleted = 0
    failed = 0

    for agent_id in agent_ids:
        try:
            success = await agent_service.delete_agent(UUID(agent_id))
            if success:
                deleted += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    return {"deleted": deleted, "failed": failed}


@router.post("/agents/batch-toggle")
async def batch_toggle_agents(
    agent_ids: List[str],
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enable or disable multiple agents"""
    from uuid import UUID

    agent_service = AgentService(db)
    updated = 0
    failed = 0

    for agent_id in agent_ids:
        try:
            agent = await agent_service.toggle_agent(UUID(agent_id), enabled)
            if agent:
                updated += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    return {"updated": updated, "failed": failed}
