"""
Command API Endpoints

指令管理 API，包括：
- 指令历史查询
- 指令结果提交
- 指令进度更新
- 指令重试
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import redis_service
from app.core.deps import get_current_user, get_current_superuser
from app.models.user import User
from models.command import AgentCommand, CommandStatus
from models.agent import Agent
from schemas.command import (
    CommandCreate, CommandUpdate, CommandResponse, CommandListResponse,
    CommandResultSubmit, CommandProgressUpdate, CommandQueueItem,
    CommandQueueResponse, CommandSimpleResponse, CommandQuery
)
from api.websocket import manager as ws_manager
from loguru import logger

router = APIRouter(prefix="/commands", tags=["Commands"])


# ================== 指令历史查询 ==================

@router.get("", response_model=CommandListResponse)
async def list_commands(
    agent_id: Optional[UUID] = Query(None, description="Agent ID"),
    status: Optional[str] = Query(None, description="指令状态"),
    command_type: Optional[str] = Query(None, description="指令类型"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """查询指令历史"""
    query = select(AgentCommand)

    # 构建过滤条件
    filters = []
    if agent_id:
        filters.append(AgentCommand.agent_id == agent_id)
    if status:
        filters.append(AgentCommand.status == status)
    if command_type:
        filters.append(AgentCommand.command_type == command_type)
    if start_time:
        filters.append(AgentCommand.created_at >= start_time)
    if end_time:
        filters.append(AgentCommand.created_at <= end_time)

    if filters:
        query = query.where(and_(*filters))

    # 计算总数
    count_query = select(AgentCommand.id)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = len(total_result.all())

    # 分页查询
    query = query.order_by(AgentCommand.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    commands = result.scalars().all()

    return CommandListResponse(
        items=[CommandResponse.model_validate(cmd) for cmd in commands],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{command_id}", response_model=CommandResponse)
async def get_command(
    command_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指令详情"""
    command = await db.get(AgentCommand, command_id)
    if not command:
        raise HTTPException(404, "指令不存在")

    return CommandResponse.model_validate(command)


# ================== 指令结果提交 ==================

@router.post("/{command_id}/result", response_model=CommandSimpleResponse)
async def submit_command_result(
    command_id: UUID,
    data: CommandResultSubmit,
    db: AsyncSession = Depends(get_db)
):
    """
    提交指令执行结果

    由 Agent 通过 MCP 工具调用，无需认证。
    """
    command = await db.get(AgentCommand, command_id)
    if not command:
        raise HTTPException(404, "指令不存在")

    # 更新指令状态
    command.status = data.status
    command.output = data.output
    command.error_message = data.error_message
    command.completed_at = datetime.utcnow()
    command.updated_at = datetime.utcnow()

    await db.commit()

    # 保存结果到 Redis
    await redis_service.set_command_result(
        str(command_id),
        {
            "status": data.status,
            "output": data.output,
            "error_message": data.error_message,
            "completed_at": command.completed_at.isoformat()
        }
    )

    # 移除超时监控
    await redis_service.remove_command_timeout(str(command.agent_id), str(command_id))

    # WebSocket 推送
    await ws_manager.broadcast({
        "type": "command_completed",
        "data": {
            "command_id": str(command_id),
            "agent_id": str(command.agent_id),
            "status": data.status,
            "output": data.output
        }
    })

    logger.info(f"Command {command_id} completed with status: {data.status}")

    return CommandSimpleResponse(success=True, message="结果提交成功")


# ================== 指令进度更新 ==================

@router.post("/{command_id}/progress", response_model=CommandSimpleResponse)
async def update_command_progress(
    command_id: UUID,
    data: CommandProgressUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新指令执行进度

    由 Agent 通过 MCP 工具调用，无需认证。
    """
    command = await db.get(AgentCommand, command_id)
    if not command:
        raise HTTPException(404, "指令不存在")

    # 更新进度
    command.progress = data.progress
    command.progress_message = data.message
    command.updated_at = datetime.utcnow()

    await db.commit()

    # 保存进度到 Redis
    await redis_service.set_command_progress(
        str(command_id),
        data.progress,
        data.message or ""
    )

    # WebSocket 推送
    await ws_manager.broadcast({
        "type": "command_progress",
        "data": {
            "command_id": str(command_id),
            "agent_id": str(command.agent_id),
            "progress": data.progress,
            "message": data.message
        }
    })

    return CommandSimpleResponse(success=True, message="进度更新成功")


# ================== 指令重试 ==================

@router.post("/{command_id}/retry", response_model=CommandSimpleResponse)
async def retry_command(
    command_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    重试失败的指令

    仅管理员可用。
    """
    command = await db.get(AgentCommand, command_id)
    if not command:
        raise HTTPException(404, "指令不存在")

    if command.status not in [CommandStatus.ERROR.value, CommandStatus.TIMEOUT.value]:
        raise HTTPException(400, "只能重试失败或超时的指令")

    if command.retry_count >= command.max_retries:
        raise HTTPException(400, f"已达到最大重试次数 ({command.max_retries})")

    # 重置指令状态
    command.status = CommandStatus.PENDING.value
    command.retry_count += 1
    command.output = None
    command.error_message = None
    command.progress = 0
    command.progress_message = None
    command.started_at = None
    command.completed_at = None
    command.updated_at = datetime.utcnow()

    await db.commit()

    # 重新推送到 Redis 队列
    command_data = {
        "id": str(command.id),
        "type": command.command_type,
        "content": command.content,
        "priority": command.priority,
        "timeout": command.timeout,
        "timestamp": int(command.created_at.timestamp() * 1000)
    }
    await redis_service.push_command(
        str(command.agent_id),
        command_data,
        command.priority
    )

    # WebSocket 推送
    await ws_manager.broadcast({
        "type": "command_retry",
        "data": {
            "command_id": str(command_id),
            "agent_id": str(command.agent_id),
            "retry_count": command.retry_count
        }
    })

    logger.info(f"Command {command_id} retry #{command.retry_count}")

    return CommandSimpleResponse(
        success=True,
        message=f"指令已重新入队 (重试 #{command.retry_count})",
        data={"retry_count": command.retry_count}
    )


# ================== 指令取消 ==================

@router.post("/{command_id}/cancel", response_model=CommandSimpleResponse)
async def cancel_command(
    command_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    取消指令

    仅管理员可用。
    """
    command = await db.get(AgentCommand, command_id)
    if not command:
        raise HTTPException(404, "指令不存在")

    if command.status not in [CommandStatus.PENDING.value, CommandStatus.EXECUTING.value]:
        raise HTTPException(400, "只能取消待处理或执行中的指令")

    # 更新状态
    command.status = CommandStatus.CANCELLED.value
    command.completed_at = datetime.utcnow()
    command.updated_at = datetime.utcnow()

    await db.commit()

    # 从 Redis 队列移除
    await redis_service.remove_command(str(command.agent_id), str(command_id))
    await redis_service.remove_command_timeout(str(command.agent_id), str(command_id))

    # WebSocket 推送
    await ws_manager.broadcast({
        "type": "command_cancelled",
        "data": {
            "command_id": str(command_id),
            "agent_id": str(command.agent_id)
        }
    })

    logger.info(f"Command {command_id} cancelled")

    return CommandSimpleResponse(success=True, message="指令已取消")


# ================== 指令统计 ==================

@router.get("/stats/summary")
async def get_command_stats(
    agent_id: Optional[UUID] = Query(None, description="Agent ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指令统计信息"""
    from sqlalchemy import func

    # 构建基础查询
    base_query = select(
        AgentCommand.status,
        func.count(AgentCommand.id).label("count")
    )

    if agent_id:
        base_query = base_query.where(AgentCommand.agent_id == agent_id)

    base_query = base_query.group_by(AgentCommand.status)

    result = await db.execute(base_query)
    stats = result.all()

    # 转换为字典
    status_counts = {row.status: row.count for row in stats}

    # 获取 Redis 队列中待处理的数量
    pending_in_redis = 0
    if agent_id:
        pending_in_redis = await redis_service.get_command_count(str(agent_id))

    return {
        "status_counts": status_counts,
        "pending_in_redis": pending_in_redis,
        "total": sum(status_counts.values())
    }
