"""
Redis 服务封装

提供指令队列的优先级队列操作、结果存储、超时监控等功能。
使用 Redis Sorted Set (ZSET) 实现优先级队列。
"""

import json
import time
from typing import Optional, Any
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings


class RedisService:
    """Redis 服务类，封装指令队列操作"""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None

    async def init(self):
        """初始化 Redis 连接"""
        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10
        )
        self._redis = Redis(connection_pool=self._pool)

    async def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()

    @property
    def client(self) -> Redis:
        """获取 Redis 客户端"""
        if self._redis is None:
            raise RuntimeError("Redis connection not initialized")
        return self._redis

    # ================== 指令队列操作 ==================

    async def push_command(
        self,
        agent_id: str,
        command: dict,
        priority: int = 0
    ) -> str:
        """
        推送指令到队列

        Args:
            agent_id: Agent ID
            command: 指令内容，包含 id, type, content 等字段
            priority: 优先级，默认为 0，越大越优先

        Returns:
            command_id
        """
        key = f"agent:commands:{agent_id}"
        command_json = json.dumps(command, ensure_ascii=False)

        # 使用 sorted set 存储优先级
        # score 越大优先级越高，同优先级按时间戳排序
        score = priority * 1e12 + (command.get("timestamp", 0) or 0)

        await self.client.zadd(
            key,
            {command_json: -score}  # 负号用于倒序
        )
        await self.client.expire(key, 86400)  # 24小时过期

        return command.get("id", "")

    async def pop_command(self, agent_id: str) -> Optional[dict]:
        """
        弹出优先级最高的指令

        Args:
            agent_id: Agent ID

        Returns:
            指令内容
        """
        key = f"agent:commands:{agent_id}"

        # 获取优先级最高的（score 最小的负数）
        result = await self.client.zrange(
            key,
            start=0,
            end=0,
            withscores=True
        )

        if not result:
            return None

        command_json = result[0][0]
        command = json.loads(command_json)

        # 移除该指令
        await self.client.zrem(key, command_json)

        return command

    async def get_commands(self, agent_id: str, limit: int = 10) -> list[dict]:
        """
        获取指定数量的指令（不移除）

        Args:
            agent_id: Agent ID
            limit: 最大数量

        Returns:
            指令列表
        """
        key = f"agent:commands:{agent_id}"

        results = await self.client.zrange(
            key,
            start=0,
            end=limit - 1,
            withscores=True
        )

        commands = []
        for command_json, _ in results:
            commands.append(json.loads(command_json))

        return commands

    async def peek_command(self, agent_id: str) -> Optional[dict]:
        """
        查看最高优先级的指令（不移除）

        Args:
            agent_id: Agent ID

        Returns:
            指令内容
        """
        key = f"agent:commands:{agent_id}"

        result = await self.client.zrange(
            key,
            start=0,
            end=0,
            withscores=True
        )

        if result:
            command_json, _ = result[0]
            return json.loads(command_json)

        return None

    async def remove_command(self, agent_id: str, command_id: str) -> bool:
        """
        移除指定指令

        Args:
            agent_id: Agent ID
            command_id: 指令 ID

        Returns:
            是否移除成功
        """
        key = f"agent:commands:{agent_id}"

        # 获取队列中所有指令
        results = await self.client.zrange(key, start=0, end=-1, withscores=True)

        for command_json, score in results:
            command = json.loads(command_json)
            if command.get("id") == command_id:
                await self.client.zrem(key, command_json)
                return True

        return False

    async def clear_commands(self, agent_id: str) -> int:
        """
        清空指定 Agent 的指令队列

        Args:
            agent_id: Agent ID

        Returns:
            清空数量
        """
        key = f"agent:commands:{agent_id}"
        count = await self.client.zcard(key)
        await self.client.delete(key)
        return count

    async def get_command_count(self, agent_id: str) -> int:
        """获取队列中指令数量"""
        key = f"agent:commands:{agent_id}"
        return await self.client.zcard(key)

    # ================== 指令结果操作 ==================

    async def set_command_result(
        self,
        command_id: str,
        result: dict,
        ttl: int = 86400
    ) -> bool:
        """
        设置指令结果

        Args:
            command_id: 指令 ID
            result: 结果内容
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        key = f"command:result:{command_id}"
        result_json = json.dumps(result, ensure_ascii=False)

        success = await self.client.set(key, result_json, ex=ttl)
        return success is not None

    async def get_command_result(self, command_id: str) -> Optional[dict]:
        """
        获取指令结果

        Args:
            command_id: 指令 ID

        Returns:
            结果内容
        """
        key = f"command:result:{command_id}"
        result_json = await self.client.get(key)

        if result_json:
            return json.loads(result_json)

        return None

    async def set_command_progress(
        self,
        command_id: str,
        progress: int,
        message: str = ""
    ) -> bool:
        """
        设置指令进度

        Args:
            command_id: 指令 ID
            progress: 进度（0-100）
            message: 进度消息

        Returns:
            是否设置成功
        """
        key = f"command:progress:{command_id}"
        data = {"progress": progress, "message": message, "timestamp": int(time.time() * 1000)}
        success = await self.client.set(key, json.dumps(data), ex=3600)  # 1小时过期
        return success is not None

    async def get_command_progress(self, command_id: str) -> Optional[dict]:
        """获取指令进度"""
        key = f"command:progress:{command_id}"
        data = await self.client.get(key)

        if data:
            return json.loads(data)

        return None

    # ================== 指令超时队列操作 ==================

    async def add_command_timeout(
        self,
        command_id: str,
        agent_id: str,
        timeout: int = 300
    ) -> bool:
        """
        添加指令超时监控

        Args:
            command_id: 指令 ID
            agent_id: Agent ID
            timeout: 超时时间（秒）

        Returns:
            是否添加成功
        """
        key = f"command:timeout:{agent_id}"
        score = time.time() + timeout

        # 使用 sorted set，score 为超时时间戳
        await self.client.zadd(
            key,
            {command_id: score}
        )
        await self.client.expire(key, timeout + 86400)  # 设置过期时间

        return True

    async def get_timeout_commands(self, agent_id: str) -> list[str]:
        """
        获取已超时的指令列表

        Args:
            agent_id: Agent ID

        Returns:
            超时的指令 ID 列表
        """
        key = f"command:timeout:{agent_id}"
        now = time.time()

        # 获取已超时的指令（score 小于当前时间戳）
        results = await self.client.zrange(
            key,
            start=0,
            end=now,
            withscores=True
        )

        command_ids = [command_id for command_id, score in results if score <= now]
        return command_ids

    async def remove_command_timeout(self, agent_id: str, command_id: str) -> bool:
        """移除指令超时监控"""
        key = f"command:timeout:{agent_id}"
        result = await self.client.zrem(key, command_id)
        return result > 0

    async def get_command_status(self, command_id: str) -> Optional[dict]:
        """
        获取指令状态

        Args:
            command_id: 指令 ID

        Returns:
            指令状态，包含 result 和 progress 字段
        """
        result = await self.get_command_result(command_id)
        progress = await self.get_command_progress(command_id)

        if result or progress:
            return {"result": result, "progress": progress}

        return None


# 创建全局实例
redis_service = RedisService()
