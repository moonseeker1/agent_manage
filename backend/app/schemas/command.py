"""
Command Schemas

Pydantic schemas for command API requests and responses.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.command import CommandType, CommandStatus


# ================== Base Schemas ==================

class CommandBase(BaseModel):
    """指令基础 schema"""
    command_type: str = Field(..., description="指令类型")
    content: Dict[str, Any] = Field(default_factory=dict, description="指令内容")
    priority: int = Field(default=0, ge=0, le=100, description="优先级（0-100）")
    timeout: int = Field(default=300, ge=10, le=3600, description="超时时间（秒）")


class CommandCreate(CommandBase):
    """创建指令 schema"""
    pass


class CommandUpdate(BaseModel):
    """更新指令 schema"""
    status: Optional[str] = None
    output: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    progress_message: Optional[str] = None
    error_message: Optional[str] = None


class CommandResultSubmit(BaseModel):
    """提交指令结果 schema"""
    output: Optional[str] = Field(default=None, description="执行输出")
    status: str = Field(..., description="执行状态 (success/error)")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class CommandProgressUpdate(BaseModel):
    """更新指令进度 schema"""
    progress: int = Field(..., ge=0, le=100, description="进度（0-100）")
    message: Optional[str] = Field(default=None, description="进度消息")


# ================== Response Schemas ==================

class CommandResponse(BaseModel):
    """指令响应 schema"""
    id: UUID
    agent_id: UUID
    command_type: str
    content: Dict[str, Any]
    status: str
    priority: int
    timeout: int
    output: Optional[str] = None
    progress: int = 0
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CommandListResponse(BaseModel):
    """指令列表响应 schema"""
    items: List[CommandResponse]
    total: int
    page: int
    page_size: int


class CommandQueueItem(BaseModel):
    """队列中的指令项（用于 MCP 轮询）"""
    id: str
    type: str
    content: Dict[str, Any]
    priority: int
    timeout: int
    created_at: Optional[str] = None


class CommandQueueResponse(BaseModel):
    """队列响应 schema（用于 MCP 轮询）"""
    commands: List[CommandQueueItem]
    count: int


class CommandSimpleResponse(BaseModel):
    """简单响应 schema"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ================== Query Schemas ==================

class CommandQuery(BaseModel):
    """指令查询参数"""
    agent_id: Optional[UUID] = None
    status: Optional[str] = None
    command_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
