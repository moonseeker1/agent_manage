"""Agent configuration management API endpoints"""
import time
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_superuser
from app.core.redis import redis_service
from app.models.user import User
from app.models.agent import Agent
from app.models.mcp_server import MCPServer
from app.models.agent_config import AgentPermission, AgentMCPBinding
from app.models.permission import AgentSkillBinding
from app.models.command import AgentCommand, CommandStatus
from app.schemas.agent_config import (
    AgentPermissionCreate,
    AgentPermissionUpdate,
    AgentPermissionResponse,
    AgentMCPBindingCreate,
    AgentMCPBindingUpdate,
    AgentMCPBindingResponse,
    AgentConfigResponse,
)
from app.api.websocket import manager as ws_manager
from loguru import logger

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

    # Get skill bindings with eager loading
    skill_result = await db.execute(
        select(AgentSkillBinding)
        .where(AgentSkillBinding.agent_id == UUID(agent_id))
        .options(selectinload(AgentSkillBinding.skill))
    )
    skill_bindings = skill_result.scalars().all()
    skill_response = [
        {
            "id": str(s.id),
            "skill_id": str(s.skill_id),
            "skill_name": s.skill.name if s.skill else None,
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


# ==================== Permission Check ====================
@router.post("/{agent_id}/check-permission")
async def check_agent_permission(
    agent_id: str,
    action: str = Query(..., description="操作类型: bash/read/write/edit/web"),
    path: Optional[str] = Query(None, description="文件路径"),
    command: Optional[str] = Query(None, description="命令"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查智能体是否有执行某操作的权限"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    # Get permission
    query = select(AgentPermission).where(AgentPermission.agent_id == UUID(agent_id))
    result = await db.execute(query)
    permission = result.scalar_one_or_none()

    if not permission:
        permission = AgentPermission(agent_id=UUID(agent_id))
        db.add(permission)
        await db.commit()
        await db.refresh(permission)

    # Check action permission
    action_map = {
        "bash": permission.allow_bash,
        "read": permission.allow_read,
        "write": permission.allow_write,
        "edit": permission.allow_edit,
        "web": permission.allow_web,
    }

    allowed = action_map.get(action, False)
    reason = ""

    if not allowed:
        reason = f"Agent does not have '{action}' permission"
    else:
        # Check path restrictions
        if path:
            if permission.blocked_paths and any(path.startswith(p) for p in permission.blocked_paths):
                allowed = False
                reason = f"Path '{path}' is blocked"
            elif permission.allowed_paths and permission.allowed_paths:
                if not any(path.startswith(p) for p in permission.allowed_paths):
                    allowed = False
                    reason = f"Path '{path}' is not in allowed list"

        # Check command restrictions
        if action == "bash" and command:
            if permission.blocked_commands and any(cmd in command for cmd in permission.blocked_commands):
                allowed = False
                reason = f"Command contains blocked pattern"
            elif permission.allowed_commands and permission.allowed_commands:
                cmd_name = command.split()[0] if command.split() else ""
                if cmd_name not in permission.allowed_commands:
                    allowed = False
                    reason = f"Command '{cmd_name}' is not in allowed list"

    return {"allowed": allowed, "reason": reason}


# ==================== Activity Reporting ====================
# In-memory activity log (for demo, should use database in production)
_agent_activities = {}

@router.post("/{agent_id}/activities")
async def report_agent_activity(
    agent_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上报智能体活动状态"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    # Store activity (in production, save to database)
    if agent_id not in _agent_activities:
        _agent_activities[agent_id] = []

    activity = {
        "action": data.get("action"),
        "thought": data.get("thought", ""),
        "status": data.get("status", "progress"),
        "detail": data.get("detail", {}),
        "timestamp": data.get("timestamp"),
    }
    _agent_activities[agent_id].append(activity)

    # Keep only last 100 activities
    if len(_agent_activities[agent_id]) > 100:
        _agent_activities[agent_id] = _agent_activities[agent_id][-100:]

    return {"success": True, "activity_logged": True}


@router.get("/{agent_id}/activities")
async def get_agent_activities(
    agent_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能体活动日志"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    activities = _agent_activities.get(agent_id, [])
    return {"activities": activities[-limit:]}


# ==================== Pending Commands (Redis-based) ====================

@router.get("/{agent_id}/commands")
async def get_agent_commands(
    agent_id: str,
    limit: int = Query(10, ge=1, le=50, description="获取数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取待执行的指令

    从 Redis 优先级队列获取指令。无需认证，由 MCP 工具调用。
    """
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    commands = []
    now = datetime.utcnow()

    # 从 Redis 队列获取指定数量的指令
    for _ in range(limit):
        command_data = await redis_service.pop_command(agent_id)
        if not command_data:
            break

        command_id = command_data.get("id")

        # 更新数据库中的指令状态
        db_command = await db.execute(
            select(AgentCommand).where(AgentCommand.id == UUID(command_id))
        )
        db_cmd = db_command.scalar_one_or_none()
        if db_cmd:
            db_cmd.status = CommandStatus.EXECUTING.value
            db_cmd.started_at = now
            db_cmd.updated_at = now
            await db.commit()

        # 添加超时监控
        timeout = command_data.get("timeout", 300)
        await redis_service.add_command_timeout(command_id, agent_id, timeout)

        commands.append(command_data)

    # WebSocket 推送
    if commands:
        await ws_manager.broadcast({
            "type": "commands_fetched",
            "data": {
                "agent_id": agent_id,
                "count": len(commands)
            }
        })

    return {"commands": commands, "count": len(commands)}


@router.post("/{agent_id}/commands")
async def send_agent_command(
    agent_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    向智能体发送指令（仅管理员）

    将指令推送到 Redis 优先级队列，同时保存到数据库。
    """
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    # 获取参数
    command_type = data.get("type", "task")
    content = data.get("content", {})
    priority = data.get("priority", 0)
    timeout = data.get("timeout", 300)
    max_retries = data.get("max_retries", 3)

    # 创建数据库记录
    command = AgentCommand(
        agent_id=UUID(agent_id),
        command_type=command_type,
        content=content,
        status=CommandStatus.PENDING.value,
        priority=priority,
        timeout=timeout,
        max_retries=max_retries
    )
    db.add(command)
    await db.commit()
    await db.refresh(command)

    # 构建队列数据
    command_data = {
        "id": str(command.id),
        "type": command_type,
        "content": content,
        "priority": priority,
        "timeout": timeout,
        "timestamp": int(time.time() * 1000)
    }

    # 推送到 Redis 队列
    await redis_service.push_command(agent_id, command_data, priority)

    # WebSocket 推送
    await ws_manager.broadcast({
        "type": "command_created",
        "data": {
            "command_id": str(command.id),
            "agent_id": agent_id,
            "command_type": command_type,
            "priority": priority
        }
    })

    logger.info(f"Command {command.id} created for agent {agent_id}")

    return {
        "success": True,
        "command_id": str(command.id),
        "command_queued": True
    }


# ==================== Allowed Tools ====================
@router.get("/{agent_id}/allowed-tools")
async def get_agent_allowed_tools(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能体允许使用的工具列表"""
    agent = await db.get(Agent, UUID(agent_id))
    if not agent:
        raise HTTPException(404, "智能体不存在")

    # Get MCP bindings
    mcp_result = await db.execute(
        select(AgentMCPBinding).where(
            AgentMCPBinding.agent_id == UUID(agent_id),
            AgentMCPBinding.is_enabled == True
        )
    )
    bindings = mcp_result.scalars().all()

    tools = []
    for binding in bindings:
        server = await db.get(MCPServer, binding.mcp_server_id)
        if server and server.enabled:
            # Get tools from server cache or binding config
            server_tools = server.tools_cache or []
            enabled_tools = binding.enabled_tools or []

            for tool in server_tools:
                tool_name = tool.get("name", "")
                # If enabled_tools is empty, all tools are allowed
                if not enabled_tools or tool_name in enabled_tools:
                    tools.append({
                        "name": tool_name,
                        "description": tool.get("description", ""),
                        "server_id": str(server.id),
                        "server_name": server.name,
                        "server_code": server.code,
                    })

    return {"tools": tools, "total": len(tools)}
