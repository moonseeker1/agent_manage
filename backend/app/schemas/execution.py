from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


# Execution Schemas
class ExecutionBase(BaseModel):
    input_data: Optional[dict[str, Any]] = None


class ExecutionCreate(ExecutionBase):
    pass


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: Optional[UUID] = None
    group_id: Optional[UUID] = None
    status: str
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    duration: Optional[float] = None


class ExecutionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ExecutionResponse]
    total: int
    page: int
    page_size: int


# Execution Log Schemas
class ExecutionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    execution_id: UUID
    level: str
    message: str
    metadata: Optional[dict[str, Any]] = Field(default=None, alias="log_metadata")
    created_at: datetime


class ExecutionLogListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ExecutionLogResponse]
    total: int


# Metric Schemas
class MetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    metric_name: str
    metric_value: float
    unit: Optional[str] = None
    recorded_at: datetime


class AgentMetricsSummary(BaseModel):
    agent_id: UUID
    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration: Optional[float] = None
    total_tokens_used: int = 0


class ExecutionMetricsSummary(BaseModel):
    total_executions: int
    running_executions: int
    completed_executions: int
    failed_executions: int
    avg_duration: Optional[float] = None
    executions_per_day: list[dict[str, Any]] = Field(default_factory=list)
