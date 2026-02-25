"""MCP Server models for managing MCP connections"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class MCPServerType(str, enum.Enum):
    """MCP Server connection type"""
    STDIO = "stdio"  # Local process via stdin/stdout
    SSE = "sse"      # Server-Sent Events
    HTTP = "http"    # HTTP-based


class MCPServer(Base):
    """MCP Server configuration"""
    __tablename__ = "mcp_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, comment="显示名称")
    code = Column(String(50), unique=True, nullable=False, comment="唯一标识")
    description = Column(Text, comment="描述")
    server_type = Column(
        SQLEnum(MCPServerType),
        default=MCPServerType.STDIO,
        comment="连接类型"
    )
    # For STDIO type
    command = Column(String(500), comment="执行命令")
    args = Column(JSON, default=list, comment="命令参数")
    # For SSE/HTTP type
    url = Column(String(500), comment="服务器URL")
    # Common
    env = Column(JSON, default=dict, comment="环境变量")
    headers = Column(JSON, default=dict, comment="HTTP头")
    enabled = Column(Boolean, default=True, comment="是否启用")
    # Cached tools info
    tools_cache = Column(JSON, default=list, comment="缓存的工具列表")
    resources_cache = Column(JSON, default=list, comment="缓存的资源列表")
    last_sync_at = Column(DateTime, comment="最后同步时间")
    sync_error = Column(Text, comment="同步错误信息")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tools = relationship("MCPTool", back_populates="server", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MCPServer {self.name}>"


class MCPTool(Base):
    """MCP Tool discovered from server"""
    __tablename__ = "mcp_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id = Column(UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False, comment="工具名称")
    description = Column(Text, comment="工具描述")
    input_schema = Column(JSON, default=dict, comment="输入参数schema")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    server = relationship("MCPServer", back_populates="tools")

    def __repr__(self):
        return f"<MCPTool {self.name}>"
