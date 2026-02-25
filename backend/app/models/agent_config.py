"""Agent-level configuration models"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentPermission(Base):
    """智能体权限配置 - 控制智能体可以执行的操作"""
    __tablename__ = "agent_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False)

    # 工具权限
    allow_bash = Column(Boolean, default=False, comment="允许执行Bash命令")
    allow_read = Column(Boolean, default=True, comment="允许读取文件")
    allow_write = Column(Boolean, default=False, comment="允许写入文件")
    allow_edit = Column(Boolean, default=False, comment="允许编辑文件")
    allow_web = Column(Boolean, default=False, comment="允许访问网络")

    # 路径限制
    allowed_paths = Column(ARRAY(String), default=list, comment="允许访问的路径列表")
    blocked_paths = Column(ARRAY(String), default=list, comment="禁止访问的路径列表")

    # 命令限制
    allowed_commands = Column(ARRAY(String), default=list, comment="允许执行的命令列表")
    blocked_commands = Column(ARRAY(String), default=list, comment="禁止执行的命令")

    # 执行限制
    max_execution_time = Column(Integer, default=300, comment="最大执行时间(秒)")
    max_output_size = Column(Integer, default=10000, comment="最大输出大小(KB)")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    agent = relationship("Agent", back_populates="agent_permission")

    def __repr__(self):
        return f"<AgentPermission for {self.agent_id}>"


class AgentMCPBinding(Base):
    """智能体与MCP服务器的绑定关系"""
    __tablename__ = "agent_mcp_bindings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    mcp_server_id = Column(UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)

    # 启用的工具列表（为空表示使用服务器的所有工具）
    enabled_tools = Column(ARRAY(String), default=list, comment="启用的工具列表")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=100, comment="优先级")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="mcp_bindings")
    mcp_server = relationship("MCPServer")

    def __repr__(self):
        return f"<AgentMCPBinding agent={self.agent_id} server={self.mcp_server_id}>"
