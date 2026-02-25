"""Agent configuration management API endpoints"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_superuser
from app.models.user import User
from app.models.agent import Agent
from app.models.mcp_server import MCPServer
from app.models.agent_config import AgentPermission, AgentMCPBinding
from app.models.permission import AgentSkillBinding
from app.schemas.agent_config import (
    AgentPermissionCreate,
    AgentPermissionUpdate,
    AgentPermissionResponse,
    AgentMCPBindingCreate,
    AgentMCPBindingUpdate,
    AgentMCPBindingResponse,
    AgentConfigResponse,
)

router = APIRouter(prefix="/agents", tags=["Agent Configuration"])


# ==================== Agent Permission ====================
@router.get("/{agent_id}/permission", response_model=AgentPermissionResponse)
async def get_agent_permission(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能体权限配置"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    # Get or create permission
    query = select(AgentPermission).where(AgentPermission.agent_id == UUID(agent_id))
    result = await db.execute(query)
    permission = result.scalar_one_or_none()

    if not permission:
        # Create default permission
        permission = AgentPermission(agent_id=UUID(agent_id))
        db.add(permission)
        await db.commit()
        await db.refresh(permission)

    return AgentPermissionResponse.model_validate(permission)


@router.put("/{agent_id}/permission", response_model=AgentPermissionResponse)
async def update_agent_permission(
    agent_id: str,
    data: AgentPermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """更新智能体权限配置（仅管理员）"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    # Get or create permission
    query = select(AgentPermission).where(AgentPermission.agent_id == UUID(agent_id))
    result = await db.execute(query)
    permission = result.scalar_one_or_none()

    if not permission:
        permission = AgentPermission(agent_id=UUID(agent_id))
        db.add(permission)

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(permission, key, value)

    await db.commit()
    await db.refresh(permission)

    return AgentPermissionResponse.model_validate(permission)


# ==================== Agent MCP Bindings ====================
@router.get("/{agent_id}/mcp-bindings", response_model=List[AgentMCPBindingResponse])
async def list_agent_mcp_bindings(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """列出智能体的MCP绑定"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    query = select(AgentMCPBinding).where(AgentMCPBinding.agent_id == UUID(agent_id))
    result = await db.execute(query)
    bindings = result.scalars().all()

    # Enrich with server info
    response = []
    for binding in bindings:
        server = await db.get(MCPServer, binding.mcp_server_id)
        binding_dict = AgentMCPBindingResponse.model_validate(binding).model_dump()
        binding_dict["server_name"] = server.name if server else None
        binding_dict["server_code"] = server.code if server else None
        response.append(AgentMCPBindingResponse(**binding_dict))

    return response


@router.post("/{agent_id}/mcp-bindings", response_model=AgentMCPBindingResponse, status_code=201)
async def create_agent_mcp_binding(
    agent_id: str,
    data: AgentMCPBindingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """创建智能体MCP绑定（仅管理员）"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    server = await db.get(MCPServer, UUID(data.mcp_server_id))
    if not server:
        raise HTTPException(404, "MCP服务器不存在")

    # Check if already bound
    existing = await db.execute(
        select(AgentMCPBinding).where(
            AgentMCPBinding.agent_id == UUID(agent_id),
            AgentMCPBinding.mcp_server_id == UUID(data.mcp_server_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "该MCP服务器已绑定到此智能体")

    binding = AgentMCPBinding(
        agent_id=UUID(agent_id),
        mcp_server_id=UUID(data.mcp_server_id),
        enabled_tools=data.enabled_tools,
        is_enabled=data.is_enabled,
        priority=data.priority
    )
    db.add(binding)
    await db.commit()
    await db.refresh(binding)

    response = AgentMCPBindingResponse.model_validate(binding)
    response.server_name = server.name
    response.server_code = server.code
    return response


@router.put("/{agent_id}/mcp-bindings/{binding_id}", response_model=AgentMCPBindingResponse)
async def update_agent_mcp_binding(
    agent_id: str,
    binding_id: str,
    data: AgentMCPBindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """更新智能体MCP绑定（仅管理员）"""
    binding = await db.get(AgentMCPBinding, UUID(binding_id))
    if not binding or str(binding.agent_id) != agent_id:
        raise HTTPException(404, "绑定不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(binding, key, value)

    await db.commit()
    await db.refresh(binding)

    server = await db.get(MCPServer, binding.mcp_server_id)
    response = AgentMCPBindingResponse.model_validate(binding)
    response.server_name = server.name if server else None
    response.server_code = server.code if server else None
    return response


@router.delete("/{agent_id}/mcp-bindings/{binding_id}", status_code=204)
async def delete_agent_mcp_binding(
    agent_id: str,
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """删除智能体MCP绑定（仅管理员）"""
    binding = await db.get(AgentMCPBinding, UUID(binding_id))
    if not binding or str(binding.agent_id) != agent_id:
        raise HTTPException(404, "绑定不存在")

    await db.delete(binding)
    await db.commit()


# ==================== Agent Complete Config ====================
@router.get("/{agent_id}/config", response_model=AgentConfigResponse)
async def get_agent_config(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能体完整配置（权限、MCP绑定、技能绑定）"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    # Get permission
    perm_result = await db.execute(
        select(AgentPermission).where(AgentPermission.agent_id == UUID(agent_id))
    )
    permission = perm_result.scalar_one_or_none()

    # Get MCP bindings
    mcp_result = await db.execute(
        select(AgentMCPBinding).where(AgentMCPBinding.agent_id == UUID(agent_id))
    )
    mcp_bindings = mcp_result.scalars().all()

    # Enrich MCP bindings with server info
    mcp_response = []
    for binding in mcp_bindings:
        server = await db.get(MCPServer, binding.mcp_server_id)
        binding_dict = AgentMCPBindingResponse.model_validate(binding).model_dump()
        binding_dict["server_name"] = server.name if server else None
        binding_dict["server_code"] = server.code if server else None
        mcp_response.append(binding_dict)

    # Get skill bindings
    skill_result = await db.execute(
        select(AgentSkillBinding).where(AgentSkillBinding.agent_id == UUID(agent_id))
    )
    skill_bindings = skill_result.scalars().all()
    skill_response = [
        {
            "id": str(s.id),
            "skill_id": str(s.skill_id),
            "skill_name": s.skill.name if hasattr(s, 'skill') and s.skill else None,
            "priority": s.priority,
            "is_enabled": s.is_enabled
        }
        for s in skill_bindings
    ]

    return AgentConfigResponse(
        agent_id=UUID(agent_id),
        agent_name=agent.name,
        permission=AgentPermissionResponse.model_validate(permission) if permission else None,
        mcp_bindings=mcp_response,
        skill_bindings=skill_response
    )
