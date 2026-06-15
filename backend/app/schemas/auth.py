from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.plan_permissions import normalize_tier, tier_label

UserTier = Literal["free", "premium", "vip", "admin"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: int
    email: str
    display_name: str
    tier: UserTier
    tier_label: str = ""

    @field_validator("tier", mode="before")
    @classmethod
    def _normalize_tier_field(cls, value: object) -> str:
        return normalize_tier(str(value) if value is not None else None)


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
