from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.services.agent_service import AgentGroupService
from app.schemas.agent import (
    AgentGroupCreate, AgentGroupUpdate, AgentGroupResponse,
    AgentGroupListResponse, AgentGroupMemberResponse, AddMemberRequest
)

router = APIRouter(prefix="/groups", tags=["Agent Groups"])


@router.get("", response_model=AgentGroupListResponse)
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get list of agent groups with pagination"""
    service = AgentGroupService(db)
    groups, total = await service.get_groups(
        page=page,
        page_size=page_size,
        search=search
    )

    # Transform members for response
    items = []
    for group in groups:
        members = [
            AgentGroupMemberResponse(
                id=member.id,
                agent_id=member.agent_id,
                agent_name=member.agent.name if member.agent else "Unknown",
                priority=member.priority
            )
            for member in group.members
        ]
        items.append(AgentGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            execution_mode=group.execution_mode,
            created_at=group.created_at,
            updated_at=group.updated_at,
            members=members
        ))

    return AgentGroupListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=AgentGroupResponse, status_code=201)
async def create_group(
    group_data: AgentGroupCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent group"""
    service = AgentGroupService(db)
    group = await service.create_group(group_data)

    members = [
        AgentGroupMemberResponse(
            id=member.id,
            agent_id=member.agent_id,
            agent_name=member.agent.name if member.agent else "Unknown",
            priority=member.priority
        )
        for member in group.members
    ]
    return AgentGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        execution_mode=group.execution_mode,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=members
    )


@router.get("/{group_id}", response_model=AgentGroupResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get agent group by ID"""
    service = AgentGroupService(db)
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = [
        AgentGroupMemberResponse(
            id=member.id,
            agent_id=member.agent_id,
            agent_name=member.agent.name if member.agent else "Unknown",
            priority=member.priority
        )
        for member in group.members
    ]
    return AgentGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        execution_mode=group.execution_mode,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=members
    )


@router.put("/{group_id}", response_model=AgentGroupResponse)
async def update_group(
    group_id: UUID,
    group_data: AgentGroupUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an agent group"""
    service = AgentGroupService(db)
    group = await service.update_group(group_id, group_data)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = [
        AgentGroupMemberResponse(
            id=member.id,
            agent_id=member.agent_id,
            agent_name=member.agent.name if member.agent else "Unknown",
            priority=member.priority
        )
        for member in group.members
    ]
    return AgentGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        execution_mode=group.execution_mode,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=members
    )


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an agent group"""
    service = AgentGroupService(db)
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")


@router.post("/{group_id}/members", response_model=AgentGroupMemberResponse, status_code=201)
async def add_member(
    group_id: UUID,
    member_data: AddMemberRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add an agent to a group"""
    service = AgentGroupService(db)
    member = await service.add_member(group_id, member_data.agent_id, member_data.priority)
    if not member:
        raise HTTPException(status_code=400, detail="Agent already in group or invalid agent/group")

    return AgentGroupMemberResponse(
        id=member.id,
        agent_id=member.agent_id,
        agent_name=member.agent.name if member.agent else "Unknown",
        priority=member.priority
    )


@router.delete("/{group_id}/members/{agent_id}", status_code=204)
async def remove_member(
    group_id: UUID,
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove an agent from a group"""
    service = AgentGroupService(db)
    removed = await service.remove_member(group_id, agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found in group")
