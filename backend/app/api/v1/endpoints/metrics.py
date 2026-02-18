from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.services.execution_service import ExecutionService
from app.schemas.execution import AgentMetricsSummary, ExecutionMetricsSummary

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/executions", response_model=ExecutionMetricsSummary)
async def get_execution_metrics(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """Get execution metrics summary"""
    service = ExecutionService(db)
    summary = await service.get_execution_metrics_summary(days=days)
    return ExecutionMetricsSummary(**summary)


@router.get("/agents/{agent_id}", response_model=AgentMetricsSummary)
async def get_agent_metrics(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get metrics summary for a specific agent"""
    service = ExecutionService(db)
    summary = await service.get_agent_metrics_summary(agent_id)
    return AgentMetricsSummary(**summary)


@router.get("/agents")
async def get_all_agent_metrics(
    db: AsyncSession = Depends(get_db)
):
    """Get metrics summary for all agents"""
    from app.services.agent_service import AgentService

    agent_service = AgentService(db)
    execution_service = ExecutionService(db)

    agents, _ = await agent_service.get_agents(page=1, page_size=1000)

    summaries = []
    for agent in agents:
        summary = await execution_service.get_agent_metrics_summary(agent.id)
        summaries.append(AgentMetricsSummary(**summary))

    return {"agents": summaries}
