import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class AgentType(str, enum.Enum):
    MCP = "mcp"
    OPENAI = "openai"
    CUSTOM = "custom"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    group_memberships = relationship("AgentGroupMember", back_populates="agent", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="agent")
    metrics = relationship("Metric", back_populates="agent")
    agent_permission = relationship("AgentPermission", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    mcp_bindings = relationship("AgentMCPBinding", back_populates="agent", cascade="all, delete-orphan")
    skill_bindings = relationship("AgentSkillBinding", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agent {self.name} ({self.agent_type})>"


class AgentGroup(Base):
    __tablename__ = "agent_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    execution_mode = Column(String(50), default="sequential")  # sequential, parallel, round_robin
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("AgentGroupMember", back_populates="group", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="group")

    def __repr__(self):
        return f"<AgentGroup {self.name}>"


class AgentGroupMember(Base):
    __tablename__ = "agent_group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("agent_groups.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("AgentGroup", back_populates="members")
    agent = relationship("Agent", back_populates="group_memberships")

    def __repr__(self):
        return f"<AgentGroupMember group={self.group_id} agent={self.agent_id}>"
