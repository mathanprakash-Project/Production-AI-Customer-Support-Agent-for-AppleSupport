"""Authentication API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

ADMIN_SECURITY_PASSPHRASE = "Tweetsupportadmin123"
SUPERADMIN_EMAIL = "mathanprakashselvam@gmail.com"


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

    # Operations Lead profile login is disabled (only agent and manager can login)
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operations Lead login is disabled. Only Support Agents and Managers can sign in.",
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

    # Operations Lead and Manager profile creation is restricted - new signups are only for Support Agents
    if user_in.role in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privileged profile creation is disabled. New accounts can only be created for Support Agents.",
        )

    target_role = "agent"
    raw_password = user_in.password.get_secret_value() if hasattr(user_in.password, "get_secret_value") else user_in.password

    new_user = User(
        email=user_in.email,
        password_hash=get_password_hash(raw_password),
        full_name=user_in.full_name,
        role=target_role,
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


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all registered users (restricted to manager role; operations lead hidden)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Manager accounts.",
        )
    # Hide any disabled operations lead/admin users from user monitoring
    res = await db.execute(select(User).where(User.role != "admin").order_by(User.created_at.desc()))
    users = res.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a user account (restricted to mathanprakashselvam@gmail.com or manager)."""
    is_super = current_user.email.lower() == SUPERADMIN_EMAIL.lower() or current_user.role == "manager"
    if not is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only the designated administrator ({SUPERADMIN_EMAIL}) has permission to delete user accounts.",
        )
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own active administrator account.",
        )

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    await db.delete(user)
    await db.commit()
    return {"message": f"User '{user.email}' successfully deleted."}

