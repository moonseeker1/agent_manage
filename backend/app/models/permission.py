"""
Skill 和权限管理模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


# 技能-权限关联表
skill_permissions = Table(
    'skill_permissions',
    Base.metadata,
    Column('skill_id', UUID(as_uuid=True), ForeignKey('skills.id', ondelete='CASCADE')),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'))
)

# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE')),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'))
)

# 用户-角色关联表
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE')),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'))
)


class Skill(Base):
    """技能模型 - 定义Agent可执行的技能"""
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)  # 技能名称
    code = Column(String(50), unique=True, nullable=False)   # 技能代码
    description = Column(Text)                                # 技能描述
    category = Column(String(50))                            # 分类
    config = Column(JSONB, default={})                       # 技能配置
    is_active = Column(Boolean, default=True)                # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    permissions = relationship("Permission", secondary=skill_permissions, back_populates="skills")

    def __repr__(self):
        return f"<Skill {self.code}: {self.name}>"


class Permission(Base):
    """权限模型 - 定义系统权限"""
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)   # 权限名称
    code = Column(String(100), unique=True, nullable=False)   # 权限代码 (如 agent:create)
    description = Column(Text)                                 # 权限描述
    resource = Column(String(50))                             # 资源类型
    action = Column(String(30))                               # 操作类型 (create/read/update/delete)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    skills = relationship("Skill", secondary=skill_permissions, back_populates="permissions")
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.code}>"


class Role(Base):
    """角色模型 - 定义用户角色"""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)    # 角色名称
    code = Column(String(50), unique=True, nullable=False)    # 角色代码
    description = Column(Text)                                 # 角色描述
    is_system = Column(Boolean, default=False)               # 是否系统角色
    is_active = Column(Boolean, default=True)                # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.code}>"
