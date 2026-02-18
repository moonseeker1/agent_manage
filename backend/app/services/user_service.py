from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_data: UserCreate, is_superuser: bool = False) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_superuser=is_superuser
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password"""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """Update user information"""
        user = await self.get_user(user_id)
        if not user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user"""
        user = await self.get_user(user_id)
        if not user:
            return False

        await self.db.delete(user)
        return True

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None
    ) -> tuple[list[User], int]:
        """List users with pagination"""
        query = select(User)

        if search:
            query = query.where(User.username.ilike(f"%{search}%"))

        # Get total count
        from sqlalchemy import func
        count_query = select(func.count()).select_from(User)
        if search:
            count_query = count_query.where(User.username.ilike(f"%{search}%"))
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(User.created_at.desc())

        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total or 0
