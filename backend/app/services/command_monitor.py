"""
Command Timeout Monitor

后台任务，定期检查超时的指令并更新状态。
"""

import asyncio
from datetime import datetime
from typing import List
from loguru import logger
from sqlalchemy import select, and_

from app.core.redis import redis_service
from app.core.database import AsyncSessionLocal
from app.models.command import AgentCommand, CommandStatus
from app.api.websocket import manager as ws_manager


class CommandMonitor:
    """指令超时监控器"""

    def __init__(self, check_interval: int = 10):
        """
        初始化监控器

        Args:
            check_interval: 检查间隔（秒）
        """
        self.check_interval = check_interval
        self._running = False

    async def start(self):
        """启动监控"""
        self._running = True
        logger.info("Command monitor started")

        while self._running:
            try:
                await self._check_timeouts()
            except Exception as e:
                logger.error(f"Error checking command timeouts: {e}")

            await asyncio.sleep(self.check_interval)

    def stop(self):
        """停止监控"""
        self._running = False
        logger.info("Command monitor stopped")

    async def _check_timeouts(self):
        """检查所有超时的指令"""
        async with AsyncSessionLocal() as db:
            # 查询正在执行且已超时的指令
            now = datetime.utcnow()

            query = select(AgentCommand).where(
                and_(
                    AgentCommand.status == CommandStatus.EXECUTING.value,
                    AgentCommand.started_at.isnot(None)
                )
            )

            result = await db.execute(query)
            executing_commands = result.scalars().all()

            timed_out = []
            for command in executing_commands:
                # 计算是否超时
                elapsed = (now - command.started_at).total_seconds()
                if elapsed > command.timeout:
                    timed_out.append(command)

            # 处理超时指令
            for command in timed_out:
                await self._handle_timeout(db, command)

            if timed_out:
                logger.info(f"Processed {len(timed_out)} timed out commands")

    async def _handle_timeout(self, db, command: AgentCommand):
        """
        处理超时指令

        Args:
            db: 数据库会话
            command: 超时的指令
        """
        agent_id = str(command.agent_id)
        command_id = str(command.id)

        logger.warning(f"Command {command_id} timed out for agent {agent_id}")

        # 检查是否可以重试
        if command.retry_count < command.max_retries:
            # 重新入队
            command.status = CommandStatus.PENDING.value
            command.retry_count += 1
            command.started_at = None
            command.updated_at = datetime.utcnow()

            # 推回 Redis 队列
            import time
            command_data = {
                "id": command_id,
                "type": command.command_type,
                "content": command.content,
                "priority": command.priority,
                "timeout": command.timeout,
                "timestamp": int(time.time() * 1000)
            }
            await redis_service.push_command(agent_id, command_data, command.priority)

            logger.info(f"Command {command_id} re-queued (retry #{command.retry_count})")

            # WebSocket 推送
            await ws_manager.broadcast({
                "type": "command_timeout_retry",
                "data": {
                    "command_id": command_id,
                    "agent_id": agent_id,
                    "retry_count": command.retry_count
                }
            })
        else:
            # 标记为超时失败
            command.status = CommandStatus.TIMEOUT.value
            command.completed_at = datetime.utcnow()
            command.updated_at = datetime.utcnow()
            command.error_message = f"Command timed out after {command.timeout} seconds (max retries reached)"

            logger.warning(f"Command {command_id} marked as timeout (max retries reached)")

            # WebSocket 推送
            await ws_manager.broadcast({
                "type": "command_timeout",
                "data": {
                    "command_id": command_id,
                    "agent_id": agent_id,
                    "error": command.error_message
                }
            })

        # 移除 Redis 超时监控
        await redis_service.remove_command_timeout(agent_id, command_id)

        await db.commit()


# 创建全局实例
command_monitor = CommandMonitor(check_interval=10)
