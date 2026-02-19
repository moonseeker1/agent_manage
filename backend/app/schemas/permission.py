"""
Skill 和权限相关的 Pydantic Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ============== Permission Schemas ==============

class PermissionBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    created_at: datetime


# ============== Role Schemas ==============

class RoleBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[str]] = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool = False
    is_active: bool = True
    created_at: datetime
    permissions: List[PermissionResponse] = []


class RoleListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[RoleResponse]
    total: int


# ============== Skill Schemas ==============

class SkillBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    category: Optional[str] = None
    config: Optional[dict] = {}


class SkillCreate(SkillBase):
    permission_ids: List[str] = []


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[str]] = None


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    category: Optional[str] = None
    config: dict = {}
    is_active: bool = True
    created_at: datetime
    permissions: List[PermissionResponse] = []


class SkillListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[SkillResponse]
    total: int


# ============== User Permission Check ==============

class UserPermissionsResponse(BaseModel):
    """用户权限汇总"""
    user_id: UUID
    roles: List[str]
    permissions: List[str]
    skills: List[str]
