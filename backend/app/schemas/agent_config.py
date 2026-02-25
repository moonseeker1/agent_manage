"""Pydantic schemas for Agent configuration"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID


# ==================== Agent Permission ====================
class AgentPermissionBase(BaseModel):
    """Agent permission base schema"""
    allow_bash: bool = False
    allow_read: bool = True
    allow_write: bool = False
    allow_edit: bool = False
    allow_web: bool = False
    allowed_paths: List[str] = []
    blocked_paths: List[str] = []
    allowed_commands: List[str] = []
    blocked_commands: List[str] = []
    max_execution_time: int = 300
    max_output_size: int = 10000


class AgentPermissionCreate(AgentPermissionBase):
    """Agent permission create schema"""
    agent_id: Optional[str] = None


class AgentPermissionUpdate(BaseModel):
    """Agent permission update schema"""
    allow_bash: Optional[bool] = None
    allow_read: Optional[bool] = None
    allow_write: Optional[bool] = None
    allow_edit: Optional[bool] = None
    allow_web: Optional[bool] = None
    allowed_paths: Optional[List[str]] = None
    blocked_paths: Optional[List[str]] = None
    allowed_commands: Optional[List[str]] = None
    blocked_commands: Optional[List[str]] = None
    max_execution_time: Optional[int] = None
    max_output_size: Optional[int] = None


class AgentPermissionResponse(AgentPermissionBase):
    """Agent permission response schema"""
    id: UUID
    agent_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Agent MCP Binding ====================
class AgentMCPBindingBase(BaseModel):
    """Agent MCP binding base schema"""
    mcp_server_id: str
    enabled_tools: List[str] = []
    is_enabled: bool = True
    priority: int = 100


class AgentMCPBindingCreate(AgentMCPBindingBase):
    """Agent MCP binding create schema"""
    pass


class AgentMCPBindingUpdate(BaseModel):
    """Agent MCP binding update schema"""
    enabled_tools: Optional[List[str]] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


class AgentMCPBindingResponse(BaseModel):
    """Agent MCP binding response schema"""
    id: UUID
    agent_id: UUID
    mcp_server_id: UUID
    server_name: Optional[str] = None
    server_code: Optional[str] = None
    enabled_tools: List[str] = []
    is_enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Agent Config Summary ====================
class AgentConfigResponse(BaseModel):
    """Agent complete configuration response"""
    agent_id: UUID
    agent_name: str
    permission: Optional[AgentPermissionResponse] = None
    mcp_bindings: List[AgentMCPBindingResponse] = []
    skill_bindings: List[dict] = []
