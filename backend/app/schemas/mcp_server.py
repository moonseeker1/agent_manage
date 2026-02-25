"""Pydantic schemas for MCP Server management"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class MCPServerTypeSchema(BaseModel):
    """MCP Server type enum values"""
    value: str
    label: str


# Tool schemas
class MCPToolBase(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="inputSchema")

    class Config:
        populate_by_name = True


class MCPToolCreate(MCPToolBase):
    server_id: Optional[str] = None


class MCPToolResponse(MCPToolBase):
    id: UUID
    server_id: UUID
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


# MCP Server schemas
class MCPServerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    description: Optional[str] = None
    server_type: str = Field(default="stdio")
    command: Optional[str] = None
    args: Optional[List[str]] = Field(default_factory=list)
    url: Optional[str] = None
    env: Optional[Dict[str, str]] = Field(default_factory=dict)
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    enabled: bool = True


class MCPServerCreate(MCPServerBase):
    pass


class MCPServerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None


class MCPServerResponse(MCPServerBase):
    id: UUID
    tools_cache: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    resources_cache: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tools: List[MCPToolResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MCPServerListResponse(BaseModel):
    """Paginated list response"""
    items: List[MCPServerResponse]
    total: int
    page: int
    page_size: int


class MCPServerSyncResponse(BaseModel):
    """Response after syncing tools"""
    server_id: UUID
    tools_count: int
    resources_count: int
    error: Optional[str] = None
