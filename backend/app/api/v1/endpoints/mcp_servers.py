"""MCP Server management API endpoints"""
import asyncio
import json
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_superuser
from app.models.user import User
from app.models.mcp_server import MCPServer, MCPTool, MCPServerType
from app.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPServerListResponse,
    MCPServerSyncResponse,
    MCPToolResponse,
)

router = APIRouter(prefix="/mcp", tags=["MCP Server Management"])


@router.get("/servers", response_model=MCPServerListResponse)
async def list_mcp_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """列出所有MCP服务器"""
    query = select(MCPServer).options(selectinload(MCPServer.tools))

    if enabled is not None:
        query = query.where(MCPServer.enabled == enabled)

    # Count total
    count_query = select(func.count(MCPServer.id))
    if enabled is not None:
        count_query = count_query.where(MCPServer.enabled == enabled)
    total = await db.scalar(count_query)

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(MCPServer.created_at.desc())
    result = await db.execute(query)
    servers = result.scalars().all()

    return MCPServerListResponse(
        items=[MCPServerResponse.model_validate(s) for s in servers],
        total=total or 0,
        page=page,
        page_size=page_size
    )


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取MCP服务器详情"""
    server = await db.get(MCPServer, UUID(server_id))
    if not server:
        raise HTTPException(404, "MCP服务器不存在")

    # Load tools relationship
    query = select(MCPServer).options(selectinload(MCPServer.tools)).where(MCPServer.id == UUID(server_id))
    result = await db.execute(query)
    server = result.scalar_one()

    return MCPServerResponse.model_validate(server)


@router.post("/servers", response_model=MCPServerResponse, status_code=201)
async def create_mcp_server(
    data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """创建MCP服务器（仅管理员）"""
    # Check if code exists
    existing = await db.execute(
        select(MCPServer).where(MCPServer.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "服务器代码已存在")

    # Validate server type
    try:
        server_type = MCPServerType(data.server_type)
    except ValueError:
        raise HTTPException(400, f"无效的服务器类型: {data.server_type}")

    # Validate required fields based on type
    if server_type == MCPServerType.STDIO and not data.command:
        raise HTTPException(400, "STDIO类型服务器需要提供command")
    elif server_type in [MCPServerType.SSE, MCPServerType.HTTP] and not data.url:
        raise HTTPException(400, f"{server_type.value}类型服务器需要提供url")

    server = MCPServer(
        name=data.name,
        code=data.code,
        description=data.description,
        server_type=server_type,
        command=data.command,
        args=data.args or [],
        url=data.url,
        env=data.env or {},
        headers=data.headers or {},
        enabled=data.enabled
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)

    return MCPServerResponse.model_validate(server)


@router.put("/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: str,
    data: MCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """更新MCP服务器（仅管理员）"""
    server = await db.get(MCPServer, UUID(server_id))
    if not server:
        raise HTTPException(404, "MCP服务器不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(server, key, value)

    await db.commit()
    await db.refresh(server)

    # Load tools for response
    query = select(MCPServer).options(selectinload(MCPServer.tools)).where(MCPServer.id == UUID(server_id))
    result = await db.execute(query)
    server = result.scalar_one()

    return MCPServerResponse.model_validate(server)


@router.delete("/servers/{server_id}", status_code=204)
async def delete_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """删除MCP服务器（仅管理员）"""
    server = await db.get(MCPServer, UUID(server_id))
    if not server:
        raise HTTPException(404, "MCP服务器不存在")

    await db.delete(server)
    await db.commit()


@router.post("/servers/{server_id}/sync", response_model=MCPServerSyncResponse)
async def sync_mcp_server_tools(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """同步MCP服务器的工具列表（仅管理员）"""
    server = await db.get(MCPServer, UUID(server_id))
    if not server:
        raise HTTPException(404, "MCP服务器不存在")

    try:
        # Try to connect and list tools
        tools, resources = await _fetch_mcp_tools(server)

        # Update tools in database
        # First delete existing tools
        await db.execute(
            select(MCPTool).where(MCPTool.server_id == server.id)
        )
        existing_tools = (await db.execute(
            select(MCPTool).where(MCPTool.server_id == server.id)
        )).scalars().all()

        for tool in existing_tools:
            await db.delete(tool)

        # Add new tools
        for tool_info in tools:
            tool = MCPTool(
                server_id=server.id,
                name=tool_info.get("name", ""),
                description=tool_info.get("description", ""),
                input_schema=tool_info.get("inputSchema", {}),
                is_enabled=True
            )
            db.add(tool)

        # Update server cache
        server.tools_cache = tools
        server.resources_cache = resources
        server.last_sync_at = datetime.utcnow()
        server.sync_error = None

        await db.commit()

        return MCPServerSyncResponse(
            server_id=server.id,
            tools_count=len(tools),
            resources_count=len(resources)
        )

    except Exception as e:
        # Update error
        server.sync_error = str(e)
        server.last_sync_at = datetime.utcnow()
        await db.commit()

        return MCPServerSyncResponse(
            server_id=server.id,
            tools_count=0,
            resources_count=0,
            error=str(e)
        )


async def _fetch_mcp_tools(server: MCPServer) -> tuple:
    """Fetch tools from MCP server"""
    tools = []
    resources = []

    if server.server_type == MCPServerType.STDIO:
        # For STDIO type, we simulate tool discovery
        # In production, this would actually spawn the process and communicate via MCP protocol
        # For now, return mock data or parse from config
        if server.code in ["agent-manager", "agent_manager"]:
            # Agent manager has predefined tools
            tools = _get_agent_manager_tools()
        else:
            # Try to discover tools (simplified)
            tools = []
    else:
        # For SSE/HTTP, try to fetch from endpoint
        # This is a placeholder for actual implementation
        pass

    return tools, resources


def _get_agent_manager_tools():
    """Get predefined tools for agent manager"""
    return [
        {"name": "agent_list", "description": "列出所有智能体"},
        {"name": "agent_get", "description": "获取智能体详情"},
        {"name": "agent_create", "description": "创建新的智能体"},
        {"name": "agent_update", "description": "更新智能体配置"},
        {"name": "agent_delete", "description": "删除智能体"},
        {"name": "agent_execute", "description": "执行智能体"},
        {"name": "execution_status", "description": "查看执行状态"},
        {"name": "execution_logs", "description": "查看执行日志"},
        {"name": "group_list", "description": "列出智能体群组"},
        {"name": "group_create", "description": "创建智能体群组"},
        {"name": "skill_list", "description": "列出所有技能"},
        {"name": "skill_create", "description": "创建技能"},
        {"name": "permission_list", "description": "列出所有权限"},
        {"name": "role_list", "description": "列出所有角色"},
    ]


@router.get("/servers/{server_id}/tools", response_model=list[MCPToolResponse])
async def list_server_tools(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """列出MCP服务器的工具"""
    server = await db.get(MCPServer, UUID(server_id))
    if not server:
        raise HTTPException(404, "MCP服务器不存在")

    tools = await db.execute(
        select(MCPTool).where(MCPTool.server_id == UUID(server_id)).order_by(MCPTool.name)
    )
    return [MCPToolResponse.model_validate(t) for t in tools.scalars().all()]


@router.put("/tools/{tool_id}/toggle", response_model=MCPToolResponse)
async def toggle_tool(
    tool_id: str,
    enabled: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """启用/禁用MCP工具（仅管理员）"""
    tool = await db.get(MCPTool, UUID(tool_id))
    if not tool:
        raise HTTPException(404, "工具不存在")

    tool.is_enabled = enabled
    await db.commit()
    await db.refresh(tool)

    return MCPToolResponse.model_validate(tool)


@router.get("/types", response_model=list)
async def get_server_types(
    current_user: User = Depends(get_current_user)
):
    """获取可用的MCP服务器类型"""
    return [
        {"value": "stdio", "label": "STDIO (本地进程)"},
        {"value": "sse", "label": "SSE (Server-Sent Events)"},
        {"value": "http", "label": "HTTP"},
    ]
