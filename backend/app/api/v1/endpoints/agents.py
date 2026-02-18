from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.services.agent_service import AgentService
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse, AgentListResponse
)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    agent_type: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get list of agents with filtering and pagination"""
    service = AgentService(db)
    agents, total = await service.get_agents(
        page=page,
        page_size=page_size,
        agent_type=agent_type,
        enabled=enabled,
        search=search
    )
    return AgentListResponse(
        items=[AgentResponse.model_validate(a) for a in agents],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent"""
    service = AgentService(db)
    agent = await service.create_agent(agent_data)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get agent by ID"""
    service = AgentService(db)
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an agent"""
    service = AgentService(db)
    agent = await service.update_agent(agent_id, agent_data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an agent"""
    service = AgentService(db)
    deleted = await service.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/{agent_id}/enable", response_model=AgentResponse)
async def enable_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Enable an agent"""
    service = AgentService(db)
    agent = await service.toggle_agent(agent_id, True)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.post("/{agent_id}/disable", response_model=AgentResponse)
async def disable_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Disable an agent"""
    service = AgentService(db)
    agent = await service.toggle_agent(agent_id, False)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)
