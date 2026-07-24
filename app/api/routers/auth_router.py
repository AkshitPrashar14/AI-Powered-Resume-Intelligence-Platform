"""
Authentication Router
=====================
Endpoints: register, login, logout, and get current user.

Public endpoints:
    POST /auth/register
    POST /auth/login

Protected endpoints:
    GET  /auth/me
    POST /auth/logout
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.repositories.user_repository import UserRepository
from app.models.user import User
from app.schemas.schemas import UserCreate, UserResponse, TokenResponse
from app.services.auth_service import AuthService, get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    user_repo = UserRepository(db)

    if await user_repo.email_exists(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    hashed_password = AuthService.get_password_hash(user_in.password)

    new_user = User(
        name=user_in.name,
        email=user_in.email.lower().strip(),
        password_hash=hashed_password,
    )

    created_user = await user_repo.create(
        name=user_in.name,
        email=user_in.email.lower().strip(),
        password_hash=hashed_password,
    )
    return created_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT token",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email + password. Returns JWT access token."""
    user_repo = UserRepository(db)

    user = await user_repo.get_by_email(form_data.username)
    if not user or not AuthService.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    access_token = AuthService.create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post(
    "/logout",
    summary="Logout (client-side token invalidation)",
    status_code=status.HTTP_200_OK,
)
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint.

    JWT tokens are stateless — invalidation is handled client-side
    by discarding the token. This endpoint confirms the token is valid
    before the client discards it.
    """
    return {"message": f"User {current_user.email} logged out successfully"}
