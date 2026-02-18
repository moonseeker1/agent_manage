from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
import enum


class AgentType(str, enum.Enum):
    MCP = "mcp"
    OPENAI = "openai"
    CUSTOM = "custom"


# Agent Schemas
class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    agent_type: AgentType
    config: dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    enabled: bool = True


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class AgentResponse(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enabled: bool
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AgentResponse]
    total: int
    page: int
    page_size: int


# Agent Group Schemas
class AgentGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    execution_mode: str = Field(default="sequential")


class AgentGroupCreate(AgentGroupBase):
    agent_ids: list[UUID] = Field(default_factory=list)


class AgentGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    execution_mode: Optional[str] = None


class AgentGroupMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    agent_name: str
    priority: int


class AgentGroupResponse(AgentGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    members: list[AgentGroupMemberResponse] = Field(default_factory=list)


class AgentGroupListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AgentGroupResponse]
    total: int
    page: int
    page_size: int


# Member management
class AddMemberRequest(BaseModel):
    agent_id: UUID
    priority: int = 0
