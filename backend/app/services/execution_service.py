from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from app.models.execution import Execution, ExecutionLog, Metric, ExecutionStatus
from app.models.agent import Agent


class ExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution(
        self,
        agent_id: Optional[UUID] = None,
        group_id: Optional[UUID] = None,
        input_data: Optional[dict] = None
    ) -> Execution:
        """Create a new execution"""
        execution = Execution(
            agent_id=agent_id,
            group_id=group_id,
            input_data=input_data,
            status=ExecutionStatus.PENDING
        )
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def get_execution(self, execution_id: UUID) -> Optional[Execution]:
        """Get execution by ID"""
        result = await self.db.execute(
            select(Execution)
            .options(selectinload(Execution.logs))
            .where(Execution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def get_executions(
        self,
        page: int = 1,
        page_size: int = 10,
        agent_id: Optional[UUID] = None,
        group_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> tuple[list[Execution], int]:
        """Get executions with filtering and pagination"""
        query = select(Execution).options(
            selectinload(Execution.agent),
            selectinload(Execution.group)
        )

        # Apply filters
        conditions = []
        if agent_id:
            conditions.append(Execution.agent_id == agent_id)
        if group_id:
            conditions.append(Execution.group_id == group_id)
        if status:
            conditions.append(Execution.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(desc(Execution.created_at))

        result = await self.db.execute(query)
        executions = result.scalars().unique().all()

        return list(executions), total or 0

    async def start_execution(self, execution_id: UUID) -> Optional[Execution]:
        """Mark execution as started"""
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def complete_execution(
        self,
        execution_id: UUID,
        output_data: Optional[dict] = None,
        error_message: Optional[str] = None
    ) -> Optional[Execution]:
        """Mark execution as completed or failed"""
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        if error_message:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = error_message
        else:
            execution.status = ExecutionStatus.COMPLETED
            execution.output_data = output_data

        execution.completed_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def cancel_execution(self, execution_id: UUID) -> Optional[Execution]:
        """Cancel an execution"""
        execution = await self.get_execution(execution_id)
        if not execution or execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            return None

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def add_log(
        self,
        execution_id: UUID,
        level: str,
        message: str,
        metadata: Optional[dict] = None
    ) -> ExecutionLog:
        """Add a log entry to an execution"""
        log = ExecutionLog(
            execution_id=execution_id,
            level=level,
            message=message,
            metadata=metadata
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_logs(self, execution_id: UUID) -> list[ExecutionLog]:
        """Get all logs for an execution"""
        result = await self.db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.created_at)
        )
        return list(result.scalars().all())

    async def add_metric(
        self,
        metric_name: str,
        metric_value: float,
        agent_id: Optional[UUID] = None,
        execution_id: Optional[UUID] = None,
        unit: Optional[str] = None
    ) -> Metric:
        """Add a metric record"""
        metric = Metric(
            agent_id=agent_id,
            execution_id=execution_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit
        )
        self.db.add(metric)
        await self.db.flush()
        await self.db.refresh(metric)
        return metric

    async def get_execution_metrics_summary(self, days: int = 7) -> dict:
        """Get execution metrics summary"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Total by status
        status_counts = await self.db.execute(
            select(Execution.status, func.count(Execution.id))
            .where(Execution.created_at >= start_date)
            .group_by(Execution.status)
        )
        status_dict = dict(status_counts.all())

        # Average duration for completed executions
        avg_duration_result = await self.db.execute(
            select(func.avg(
                func.extract('epoch', Execution.completed_at - Execution.started_at)
            ))
            .where(
                and_(
                    Execution.created_at >= start_date,
                    Execution.status == ExecutionStatus.COMPLETED,
                    Execution.started_at.isnot(None),
                    Execution.completed_at.isnot(None)
                )
            )
        )
        avg_duration = avg_duration_result.scalar()

        # Executions per day
        daily_stats = await self.db.execute(
            select(
                func.date(Execution.created_at).label('date'),
                func.count(Execution.id).label('count')
            )
            .where(Execution.created_at >= start_date)
            .group_by(func.date(Execution.created_at))
            .order_by(func.date(Execution.created_at))
        )

        return {
            "total_executions": sum(status_dict.values()),
            "running_executions": status_dict.get(ExecutionStatus.RUNNING, 0),
            "completed_executions": status_dict.get(ExecutionStatus.COMPLETED, 0),
            "failed_executions": status_dict.get(ExecutionStatus.FAILED, 0),
            "cancelled_executions": status_dict.get(ExecutionStatus.CANCELLED, 0),
            "avg_duration": float(avg_duration) if avg_duration else None,
            "executions_per_day": [
                {"date": str(row.date), "count": row.count}
                for row in daily_stats.all()
            ]
        }

    async def get_agent_metrics_summary(self, agent_id: UUID) -> dict:
        """Get metrics summary for a specific agent"""
        # Total executions
        total = await self.db.scalar(
            select(func.count(Execution.id)).where(Execution.agent_id == agent_id)
        )

        # Successful executions
        successful = await self.db.scalar(
            select(func.count(Execution.id)).where(
                and_(
                    Execution.agent_id == agent_id,
                    Execution.status == ExecutionStatus.COMPLETED
                )
            )
        )

        # Failed executions
        failed = await self.db.scalar(
            select(func.count(Execution.id)).where(
                and_(
                    Execution.agent_id == agent_id,
                    Execution.status == ExecutionStatus.FAILED
                )
            )
        )

        # Average duration
        avg_duration = await self.db.scalar(
            select(func.avg(
                func.extract('epoch', Execution.completed_at - Execution.started_at)
            ))
            .where(
                and_(
                    Execution.agent_id == agent_id,
                    Execution.status == ExecutionStatus.COMPLETED,
                    Execution.started_at.isnot(None),
                    Execution.completed_at.isnot(None)
                )
            )
        )

        # Get agent name
        agent = await self.db.execute(select(Agent.name).where(Agent.id == agent_id))
        agent_name = agent.scalar() or "Unknown"

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "total_executions": total or 0,
            "successful_executions": successful or 0,
            "failed_executions": failed or 0,
            "success_rate": (successful / total * 100) if total else 0,
            "avg_duration": float(avg_duration) if avg_duration else None,
            "total_tokens_used": 0  # Would need to track this separately
        }
