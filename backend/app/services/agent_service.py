from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID
from app.models.agent import Agent, AgentGroup, AgentGroupMember
from app.schemas.agent import AgentCreate, AgentUpdate, AgentGroupCreate, AgentGroupUpdate


class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_agent(self, agent_data: AgentCreate) -> Agent:
        """Create a new agent"""
        agent = Agent(
            name=agent_data.name,
            description=agent_data.description,
            agent_type=agent_data.agent_type.value,
            config=agent_data.config,
            enabled=agent_data.enabled
        )
        self.db.add(agent)
        await self.db.flush()
        await self.db.refresh(agent)
        return agent

    async def get_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent by ID"""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_agents(
        self,
        page: int = 1,
        page_size: int = 10,
        agent_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        search: Optional[str] = None
    ) -> tuple[list[Agent], int]:
        """Get agents with filtering and pagination"""
        query = select(Agent)

        # Apply filters
        conditions = []
        if agent_type:
            conditions.append(Agent.agent_type == agent_type)
        if enabled is not None:
            conditions.append(Agent.enabled == enabled)
        if search:
            conditions.append(Agent.name.ilike(f"%{search}%"))

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Agent.created_at.desc())

        result = await self.db.execute(query)
        agents = result.scalars().all()

        return list(agents), total or 0

    async def update_agent(self, agent_id: UUID, agent_data: AgentUpdate) -> Optional[Agent]:
        """Update an agent"""
        agent = await self.get_agent(agent_id)
        if not agent:
            return None

        update_data = agent_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, value)

        await self.db.flush()
        await self.db.refresh(agent)
        return agent

    async def delete_agent(self, agent_id: UUID) -> bool:
        """Delete an agent"""
        agent = await self.get_agent(agent_id)
        if not agent:
            return False

        await self.db.delete(agent)
        return True

    async def toggle_agent(self, agent_id: UUID, enabled: bool) -> Optional[Agent]:
        """Enable or disable an agent"""
        agent = await self.get_agent(agent_id)
        if not agent:
            return None

        agent.enabled = enabled
        await self.db.flush()
        await self.db.refresh(agent)
        return agent


class AgentGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_group(self, group_data: AgentGroupCreate) -> AgentGroup:
        """Create a new agent group"""
        group = AgentGroup(
            name=group_data.name,
            description=group_data.description,
            execution_mode=group_data.execution_mode
        )
        self.db.add(group)
        await self.db.flush()

        # Add members
        for priority, agent_id in enumerate(group_data.agent_ids):
            member = AgentGroupMember(
                group_id=group.id,
                agent_id=agent_id,
                priority=priority
            )
            self.db.add(member)

        await self.db.refresh(group)
        return await self.get_group(group.id)

    async def get_group(self, group_id: UUID) -> Optional[AgentGroup]:
        """Get group by ID with members"""
        result = await self.db.execute(
            select(AgentGroup)
            .options(selectinload(AgentGroup.members).selectinload(AgentGroupMember.agent))
            .where(AgentGroup.id == group_id)
        )
        return result.scalar_one_or_none()

    async def get_groups(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None
    ) -> tuple[list[AgentGroup], int]:
        """Get groups with pagination"""
        query = select(AgentGroup).options(
            selectinload(AgentGroup.members).selectinload(AgentGroupMember.agent)
        )

        if search:
            query = query.where(AgentGroup.name.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(AgentGroup)
        if search:
            count_query = count_query.where(AgentGroup.name.ilike(f"%{search}%"))
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(AgentGroup.created_at.desc())

        result = await self.db.execute(query)
        groups = result.scalars().unique().all()

        return list(groups), total or 0

    async def update_group(self, group_id: UUID, group_data: AgentGroupUpdate) -> Optional[AgentGroup]:
        """Update a group"""
        group = await self.get_group(group_id)
        if not group:
            return None

        update_data = group_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(group, field, value)

        await self.db.flush()
        await self.db.refresh(group)
        return await self.get_group(group_id)

    async def delete_group(self, group_id: UUID) -> bool:
        """Delete a group"""
        group = await self.get_group(group_id)
        if not group:
            return False

        await self.db.delete(group)
        return True

    async def add_member(self, group_id: UUID, agent_id: UUID, priority: int = 0) -> Optional[AgentGroupMember]:
        """Add an agent to a group"""
        # Check if already a member
        existing = await self.db.execute(
            select(AgentGroupMember).where(
                and_(AgentGroupMember.group_id == group_id, AgentGroupMember.agent_id == agent_id)
            )
        )
        if existing.scalar_one_or_none():
            return None

        member = AgentGroupMember(
            group_id=group_id,
            agent_id=agent_id,
            priority=priority
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def remove_member(self, group_id: UUID, agent_id: UUID) -> bool:
        """Remove an agent from a group"""
        result = await self.db.execute(
            select(AgentGroupMember).where(
                and_(AgentGroupMember.group_id == group_id, AgentGroupMember.agent_id == agent_id)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False

        await self.db.delete(member)
        return True
