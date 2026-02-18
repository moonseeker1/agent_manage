from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.services.user_service import UserService

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user_service = UserService(db)
    user = await user_service.get_user(UUID(user_id))

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user is superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


# Optional authentication - doesn't raise error if no token
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        return None

    user_id: str = payload.get("sub")
    if not user_id:
        return None

    user_service = UserService(db)
    user = await user_service.get_user(UUID(user_id))

    return user
