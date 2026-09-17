"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Log in with email and password to receive a JWT access token."""
    res = await db.execute(select(User).where(User.email == credentials.email))
    user = res.scalars().first()

    raw_password = credentials.password.get_secret_value() if hasattr(credentials.password, "get_secret_value") else credentials.password

    if not user or not verify_password(raw_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account and return a JWT access token."""
    res = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = res.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    raw_password = user_in.password.get_secret_value() if hasattr(user_in.password, "get_secret_value") else user_in.password

    new_user = User(
        email=user_in.email,
        password_hash=get_password_hash(raw_password),
        full_name=user_in.full_name,
        role=user_in.role if user_in.role in ["agent", "admin"] else "agent",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token({"sub": new_user.id, "email": new_user.email, "role": new_user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )

