"""
Agent Command Model

指令模型，用于存储发送给 Agent 的指令及其执行状态。
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CommandType(str, enum.Enum):
    """指令类型"""
    PAUSE = "pause"              # 暂停当前任务
    CANCEL = "cancel"            # 取消当前任务
    TASK = "task"                # 新任务
    CONFIG_RELOAD = "config_reload"  # 重新加载配置
    STATUS_CHECK = "status_check"    # 状态检查


class CommandStatus(str, enum.Enum):
    """指令状态"""
    PENDING = "pending"          # 待处理（在队列中）
    EXECUTING = "executing"      # 执行中
    SUCCESS = "success"          # 执行成功
    ERROR = "error"              # 执行失败
    TIMEOUT = "timeout"          # 超时
    CANCELLED = "cancelled"      # 已取消


class AgentCommand(Base):
    """Agent 指令模型"""
    __tablename__ = "agent_commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    # 指令类型和内容
    command_type = Column(String(50), nullable=False)
    content = Column(JSON, nullable=False, default=dict)

    # 状态
    status = Column(String(20), default=CommandStatus.PENDING.value)

    # 优先级和超时
    priority = Column(Integer, default=0)       # 优先级，越大越优先
    timeout = Column(Integer, default=300)      # 超时时间（秒）

    # 执行信息
    output = Column(Text, nullable=True)
    progress = Column(Integer, default=0)       # 进度（0-100）
    progress_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)    # 最大重试次数

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    agent = relationship("Agent", back_populates="commands")

    def __repr__(self):
        return f"<AgentCommand {self.id} agent={self.agent_id} type={self.command_type} status={self.status}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "command_type": self.command_type,
            "content": self.content,
            "status": self.status,
            "priority": self.priority,
            "timeout": self.timeout,
            "output": self.output,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
