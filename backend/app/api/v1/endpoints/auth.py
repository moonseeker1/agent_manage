from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.core.deps import get_current_user, get_current_superuser
from app.services.user_service import UserService
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, UserUpdate, Token
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    user_service = UserService(db)

    # Check if username exists
    existing_user = await user_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    existing_email = await user_service.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = await user_service.create_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token"""
    user_service = UserService(db)
    user = await user_service.authenticate(user_data.username, user_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Get current user info"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user info"""
    user_service = UserService(db)
    user = await user_service.update_user(current_user.id, user_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


# Admin endpoints
@router.get("/users", response_model=dict)
async def list_users(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    user_service = UserService(db)
    users, total = await user_service.list_users(page, page_size, search)

    return {
        "items": [UserResponse.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (admin only)"""
    from uuid import UUID

    user_service = UserService(db)
    deleted = await user_service.delete_user(UUID(user_id))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
