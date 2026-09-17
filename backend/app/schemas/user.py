"""Pydantic schemas for User authentication and profiles."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class UserBase(BaseModel):
    email: str = Field(..., min_length=3)
    full_name: str = "Support Agent"
    role: str = "agent"


class UserCreate(UserBase):
    password: SecretStr = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: str
    password: SecretStr


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

