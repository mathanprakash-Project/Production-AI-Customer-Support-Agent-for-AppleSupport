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

    target_role = user_in.role if user_in.role in ["agent", "admin", "manager"] else "agent"

    # Security check for privileged roles (Operations Lead & Manager-Users)
    if target_role in ["admin", "manager"]:
        raw_secret = ""
        if user_in.security_answer:
            raw_secret = (
                user_in.security_answer.get_secret_value()
                if hasattr(user_in.security_answer, "get_secret_value")
                else str(user_in.security_answer)
            )

        if raw_secret != ADMIN_SECURITY_PASSPHRASE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid security passphrase for privileged profile creation. Operations Lead and Manager accounts require valid administrator authorization.",
            )

        if target_role == "manager" and user_in.email.lower() != SUPERADMIN_EMAIL.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only the designated administrator email ({SUPERADMIN_EMAIL}) is permitted to register the Manager-Users profile.",
            )

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
    """List all registered users (restricted to admin and manager roles)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Operations Lead and Manager-Users accounts.",
        )
    res = await db.execute(select(User).order_by(User.created_at.desc()))
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

