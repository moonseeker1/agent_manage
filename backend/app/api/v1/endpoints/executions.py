from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.services.execution_service import ExecutionService
from app.schemas.execution import (
    ExecutionCreate, ExecutionResponse, ExecutionListResponse,
    ExecutionLogResponse, ExecutionLogListResponse
)
from app.services.executor import execute_agent_task, execute_group_task

router = APIRouter(prefix="/executions", tags=["Executions"])


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    agent_id: Optional[UUID] = Query(None),
    group_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get list of executions with filtering and pagination"""
    service = ExecutionService(db)
    executions, total = await service.get_executions(
        page=page,
        page_size=page_size,
        agent_id=agent_id,
        group_id=group_id,
        status=status
    )
    return ExecutionListResponse(
        items=[ExecutionResponse.model_validate(e) for e in executions],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get execution by ID"""
    service = ExecutionService(db)
    execution = await service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionResponse.model_validate(execution)


@router.get("/{execution_id}/logs", response_model=ExecutionLogListResponse)
async def get_execution_logs(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get logs for an execution"""
    service = ExecutionService(db)
    execution = await service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    logs = await service.get_logs(execution_id)
    return ExecutionLogListResponse(
        items=[ExecutionLogResponse.model_validate(log) for log in logs],
        total=len(logs)
    )


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Cancel an execution"""
    service = ExecutionService(db)
    execution = await service.cancel_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=400, detail="Execution cannot be cancelled")
    return ExecutionResponse.model_validate(execution)


# Execute single agent
@router.post("/agents/{agent_id}/execute", response_model=ExecutionResponse, status_code=201)
async def execute_agent(
    agent_id: UUID,
    execution_data: ExecutionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Execute a single agent"""
    from app.services.agent_service import AgentService

    # Verify agent exists and is enabled
    agent_service = AgentService(db)
    agent = await agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.enabled:
        raise HTTPException(status_code=400, detail="Agent is disabled")

    # Create execution record
    execution_service = ExecutionService(db)
    execution = await execution_service.create_execution(
        agent_id=agent_id,
        input_data=execution_data.input_data
    )

    # Start background task
    background_tasks.add_task(
        execute_agent_task,
        str(execution.id),
        str(agent_id),
        execution_data.input_data
    )

    return ExecutionResponse.model_validate(execution)


# Execute group
@router.post("/groups/{group_id}/execute", response_model=ExecutionResponse, status_code=201)
async def execute_group(
    group_id: UUID,
    execution_data: ExecutionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Execute an agent group"""
    from app.services.agent_service import AgentGroupService

    # Verify group exists
    group_service = AgentGroupService(db)
    group = await group_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Create execution record
    execution_service = ExecutionService(db)
    execution = await execution_service.create_execution(
        group_id=group_id,
        input_data=execution_data.input_data
    )

    # Start background task
    background_tasks.add_task(
        execute_group_task,
        str(execution.id),
        str(group_id),
        execution_data.input_data
    )

    return ExecutionResponse.model_validate(execution)
