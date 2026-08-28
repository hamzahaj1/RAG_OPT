# [FILE] — app/domains/users/schemas.py
# [SCHEMA]
# synthesis: The 4 Pydantic schemas of the users domain carry the contract of the User entity.
# domain: users
# schemas: UserBase(BaseModel), UserCreate(UserBase), UserRead(UserBase), UserUpdate(BaseModel)
# entity: User
# [/SCHEMA]
"""Pydantic schemas of the users domain.

Pure data, no logic and no methods: four classes (Base, Create, Read,
Update) in alphabetical order. No schema ever exposes the password,
cleartext or hashed (FR-009); maximum lengths are aligned with the
``models.py`` columns.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domains.users.models import UserRole

# ──────────────

# [CODE_START]


class UserBase(BaseModel):
    """Fields shared by user writes and reads."""

    email: EmailStr = Field(max_length=255)
    full_name: str = Field(max_length=100)
    role: UserRole


class UserCreate(UserBase):
    """POST body — shared fields plus the cleartext password (min 8)."""

    password: str = Field(min_length=8)


class UserRead(UserBase):
    """API response — never a password field, cleartext or hashed."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """PATCH body — all fields optional, ``exclude_unset`` semantics."""

    email: EmailStr | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
