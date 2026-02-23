"""
技能和权限管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_superuser
from app.models.user import User
from app.models.agent import Agent
from app.models.permission import (
    Skill, Permission, Role, AgentSkillBinding, AuditLog,
    skill_permissions, role_permissions, user_roles
)
from app.schemas.permission import (
    PermissionCreate, PermissionUpdate, PermissionResponse,
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    SkillCreate, SkillUpdate, SkillResponse, SkillListResponse,
    UserPermissionsResponse
)
from pydantic import BaseModel


# Agent Skill Binding Schemas
class AgentSkillBindingCreate(BaseModel):
    agent_id: str
    skill_id: str
    config: dict = {}
    priority: int = 100
    is_enabled: bool = True


class AgentSkillBindingUpdate(BaseModel):
    config: Optional[dict] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None


class AgentSkillBindingResponse(BaseModel):
    id: str
    agent_id: str
    skill_id: str
    skill_name: str
    skill_code: str
    config: dict
    priority: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Audit Log Schema
class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    detail: dict
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

router = APIRouter(prefix="/rbac", tags=["RBAC - 技能与权限管理"])


# ============== Permission Management ==============

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取权限列表"""
    query = select(Permission)
    if resource:
        query = query.where(Permission.resource == resource)
    query = query.order_by(Permission.resource, Permission.action)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/permissions", response_model=PermissionResponse, status_code=201)
async def create_permission(
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """创建权限（仅管理员）"""
    # 检查是否已存在
    existing = await db.execute(
        select(Permission).where(Permission.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "权限代码已存在")

    permission = Permission(**data.model_dump())
    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    return permission


@router.delete("/permissions/{permission_id}", status_code=204)
async def delete_permission(
    permission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """删除权限（仅管理员）"""
    permission = await db.get(Permission, UUID(permission_id))
    if not permission:
        raise HTTPException(404, "权限不存在")

    await db.delete(permission)
    await db.commit()


# ============== Role Management ==============

@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取角色列表"""
    # Count
    total = await db.scalar(select(func.count(Role.id)))

    # Query with permissions
    query = select(Role).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    roles = result.scalars().all()

    return {"items": roles, "total": total or 0}


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """创建角色（仅管理员）"""
    # 检查是否已存在
    existing = await db.execute(
        select(Role).where(Role.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "角色代码已存在")

    permission_ids = data.permission_ids
    del data.permission_ids

    role = Role(**data.model_dump())
    db.add(role)
    await db.flush()

    # 添加权限
    if permission_ids:
        for pid in permission_ids:
            await db.execute(
                role_permissions.insert().values(
                    role_id=role.id,
                    permission_id=UUID(pid)
                )
            )

    await db.commit()
    await db.refresh(role)
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """更新角色（仅管理员）"""
    role = await db.get(Role, UUID(role_id))
    if not role:
        raise HTTPException(404, "角色不存在")

    if role.is_system:
        raise HTTPException(400, "系统角色不可修改")

    update_data = data.model_dump(exclude_unset=True)

    # 更新权限
    if "permission_ids" in update_data:
        permission_ids = update_data.pop("permission_ids")
        # 删除旧权限
        await db.execute(
            role_permissions.delete().where(role_permissions.c.role_id == role.id)
        )
        # 添加新权限
        for pid in permission_ids:
            await db.execute(
                role_permissions.insert().values(
                    role_id=role.id,
                    permission_id=UUID(pid)
                )
            )

    for key, value in update_data.items():
        setattr(role, key, value)

    await db.commit()
    await db.refresh(role)
    return role


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """删除角色（仅管理员）"""
    role = await db.get(Role, UUID(role_id))
    if not role:
        raise HTTPException(404, "角色不存在")

    if role.is_system:
        raise HTTPException(400, "系统角色不可删除")

    await db.delete(role)
    await db.commit()


@router.post("/roles/{role_id}/users/{user_id}", status_code=200)
async def assign_role_to_user(
    role_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """给用户分配角色（仅管理员）"""
    role = await db.get(Role, UUID(role_id))
    user = await db.get(User, UUID(user_id))

    if not role or not user:
        raise HTTPException(404, "角色或用户不存在")

    await db.execute(
        user_roles.insert().values(
            user_id=UUID(user_id),
            role_id=UUID(role_id)
        )
    )
    await db.commit()
    return {"message": "角色分配成功"}


@router.delete("/roles/{role_id}/users/{user_id}", status_code=200)
async def remove_role_from_user(
    role_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """移除用户角色（仅管理员）"""
    await db.execute(
        user_roles.delete().where(
            user_roles.c.user_id == UUID(user_id),
            user_roles.c.role_id == UUID(role_id)
        )
    )
    await db.commit()
    return {"message": "角色移除成功"}


# ============== Skill Management ==============

@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    page: int = 1,
    page_size: int = 10,
    category: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取技能列表"""
    from sqlalchemy.orm import selectinload

    query = select(Skill).options(selectinload(Skill.permissions))
    if category:
        query = query.where(Skill.category == category)

    # Count
    count_query = select(func.count()).select_from(Skill)
    if category:
        count_query = count_query.where(Skill.category == category)
    total = await db.scalar(count_query)

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    skills = result.scalars().all()

    return {"items": skills, "total": total or 0}


@router.post("/skills", response_model=SkillResponse, status_code=201)
async def create_skill(
    data: SkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """创建技能（仅管理员）"""
    existing = await db.execute(
        select(Skill).where(Skill.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "技能代码已存在")

    permission_ids = data.permission_ids
    del data.permission_ids

    skill = Skill(**data.model_dump())
    db.add(skill)
    await db.flush()

    # 添加权限
    if permission_ids:
        for pid in permission_ids:
            await db.execute(
                skill_permissions.insert().values(
                    skill_id=skill.id,
                    permission_id=UUID(pid)
                )
            )

    await db.commit()
    await db.refresh(skill)
    return skill


@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """更新技能（仅管理员）"""
    skill = await db.get(Skill, UUID(skill_id))
    if not skill:
        raise HTTPException(404, "技能不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 更新权限
    if "permission_ids" in update_data:
        permission_ids = update_data.pop("permission_ids")
        await db.execute(
            skill_permissions.delete().where(skill_permissions.c.skill_id == skill.id)
        )
        for pid in permission_ids:
            await db.execute(
                skill_permissions.insert().values(
                    skill_id=skill.id,
                    permission_id=UUID(pid)
                )
            )

    for key, value in update_data.items():
        setattr(skill, key, value)

    await db.commit()
    await db.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """删除技能（仅管理员）"""
    skill = await db.get(Skill, UUID(skill_id))
    if not skill:
        raise HTTPException(404, "技能不存在")

    await db.delete(skill)
    await db.commit()


# ============== User Permissions ==============

@router.get("/users/me/permissions", response_model=UserPermissionsResponse)
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的权限"""
    # 获取用户角色
    roles_result = await db.execute(
        select(Role).join(user_roles).where(user_roles.c.user_id == current_user.id)
    )
    roles = roles_result.scalars().all()

    # 获取所有权限
    permissions = set()
    for role in roles:
        for perm in role.permissions:
            permissions.add(perm.code)

    # 如果是超级用户，拥有所有权限
    if current_user.is_superuser:
        all_perms = await db.execute(select(Permission.code))
        permissions = set(p[0] for p in all_perms.all())

    # 获取可用技能
    skills_result = await db.execute(
        select(Skill.code).where(Skill.is_active == True)
    )
    skills = [s[0] for s in skills_result.all()]

    return {
        "user_id": current_user.id,
        "roles": [r.code for r in roles],
        "permissions": list(permissions),
        "skills": skills
    }


# ============== Agent Skill Binding ==============

@router.get("/agents/{agent_id}/skills", response_model=List[AgentSkillBindingResponse])
async def list_agent_skills(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能体绑定的技能列表"""
    result = await db.execute(
        select(AgentSkillBinding, Skill)
        .join(Skill, AgentSkillBinding.skill_id == Skill.id)
        .where(AgentSkillBinding.agent_id == UUID(agent_id))
        .order_by(AgentSkillBinding.priority)
    )
    rows = result.all()

    return [
        AgentSkillBindingResponse(
            id=str(binding.id),
            agent_id=str(binding.agent_id),
            skill_id=str(binding.skill_id),
            skill_name=skill.name,
            skill_code=skill.code,
            config=binding.config or {},
            priority=binding.priority,
            is_enabled=binding.is_enabled,
            created_at=binding.created_at,
            updated_at=binding.updated_at
        )
        for binding, skill in rows
    ]


@router.post("/agents/{agent_id}/skills/{skill_id}", response_model=AgentSkillBindingResponse, status_code=201)
async def bind_skill_to_agent(
    agent_id: str,
    skill_id: str,
    data: AgentSkillBindingCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """给智能体绑定技能（仅管理员）"""
    # 检查是否已存在
    existing = await db.execute(
        select(AgentSkillBinding).where(
            and_(
                AgentSkillBinding.agent_id == UUID(agent_id),
                AgentSkillBinding.skill_id == UUID(skill_id)
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "该技能已绑定到此智能体")

    binding = AgentSkillBinding(
        agent_id=UUID(agent_id),
        skill_id=UUID(skill_id),
        config=data.config,
        priority=data.priority,
        is_enabled=data.is_enabled
    )
    db.add(binding)

    # 审计日志
    audit = AuditLog(
        user_id=current_user.id,
        action="bind_skill",
        resource_type="agent",
        resource_id=UUID(agent_id),
        detail={"skill_id": skill_id, "priority": data.priority},
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)

    await db.commit()
    await db.refresh(binding)

    # 获取技能信息
    skill = await db.get(Skill, UUID(skill_id))

    return AgentSkillBindingResponse(
        id=str(binding.id),
        agent_id=str(binding.agent_id),
        skill_id=str(binding.skill_id),
        skill_name=skill.name if skill else "",
        skill_code=skill.code if skill else "",
        config=binding.config or {},
        priority=binding.priority,
        is_enabled=binding.is_enabled,
        created_at=binding.created_at,
        updated_at=binding.updated_at
    )


@router.put("/agents/{agent_id}/skills/{skill_id}", response_model=AgentSkillBindingResponse)
async def update_agent_skill_binding(
    agent_id: str,
    skill_id: str,
    data: AgentSkillBindingUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """更新智能体技能绑定（仅管理员）"""
    binding = await db.execute(
        select(AgentSkillBinding).where(
            and_(
                AgentSkillBinding.agent_id == UUID(agent_id),
                AgentSkillBinding.skill_id == UUID(skill_id)
            )
        )
    )
    binding = binding.scalar_one_or_none()
    if not binding:
        raise HTTPException(404, "绑定关系不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(binding, key, value)

    # 审计日志
    audit = AuditLog(
        user_id=current_user.id,
        action="update_skill_binding",
        resource_type="agent",
        resource_id=UUID(agent_id),
        detail={"skill_id": skill_id, "changes": update_data},
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)

    await db.commit()
    await db.refresh(binding)

    skill = await db.get(Skill, UUID(skill_id))

    return AgentSkillBindingResponse(
        id=str(binding.id),
        agent_id=str(binding.agent_id),
        skill_id=str(binding.skill_id),
        skill_name=skill.name if skill else "",
        skill_code=skill.code if skill else "",
        config=binding.config or {},
        priority=binding.priority,
        is_enabled=binding.is_enabled,
        created_at=binding.created_at,
        updated_at=binding.updated_at
    )


@router.delete("/agents/{agent_id}/skills/{skill_id}", status_code=204)
async def unbind_skill_from_agent(
    agent_id: str,
    skill_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """解除智能体技能绑定（仅管理员）"""
    binding = await db.execute(
        select(AgentSkillBinding).where(
            and_(
                AgentSkillBinding.agent_id == UUID(agent_id),
                AgentSkillBinding.skill_id == UUID(skill_id)
            )
        )
    )
    binding = binding.scalar_one_or_none()
    if not binding:
        raise HTTPException(404, "绑定关系不存在")

    # 审计日志
    audit = AuditLog(
        user_id=current_user.id,
        action="unbind_skill",
        resource_type="agent",
        resource_id=UUID(agent_id),
        detail={"skill_id": skill_id},
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)

    await db.delete(binding)
    await db.commit()


# ============== Audit Logs ==============

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    page: int = 1,
    page_size: int = 20,
    action: str = None,
    resource_type: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """获取审计日志（仅管理员）"""
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        AuditLogResponse(
            id=str(log.id),
            user_id=str(log.user_id) if log.user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=str(log.resource_id) if log.resource_id else None,
            detail=log.detail or {},
            ip_address=log.ip_address,
            created_at=log.created_at
        )
        for log in logs
    ]
