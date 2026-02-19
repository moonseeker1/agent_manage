"""
技能和权限管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_superuser
from app.models.user import User
from app.models.permission import Skill, Permission, Role, skill_permissions, role_permissions, user_roles
from app.schemas.permission import (
    PermissionCreate, PermissionUpdate, PermissionResponse,
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    SkillCreate, SkillUpdate, SkillResponse, SkillListResponse,
    UserPermissionsResponse
)

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
    query = select(Skill)
    if category:
        query = query.where(Skill.category == category)

    # Count
    total = await db.scalar(select(func.count()).select_from(query.subquery()))

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
