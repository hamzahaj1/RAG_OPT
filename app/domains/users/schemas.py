# [FILE] — app/domains/users/schemas.py
# [SCHEMA]
# domain: users
# schemas: UserBase(BaseModel), UserCreate(UserBase), UserRead(UserBase), UserUpdate(BaseModel)
# entity: User
# [/SCHEMA]
"""Schémas Pydantic du domaine users.

Données pures, sans logique ni méthode : quatre classes (Base, Create,
Read, Update) en ordre alphabétique. Aucun schéma n'expose jamais le mot
de passe, en clair ou haché (FR-009) ; les longueurs maximales sont
alignées sur les colonnes de ``models.py``.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domains.users.models import UserRole

# ──────────────

# [CODE_START]


class UserBase(BaseModel):
    """Champs communs aux écritures et aux lectures d'un utilisateur."""

    email: EmailStr = Field(max_length=255)
    full_name: str = Field(max_length=100)
    role: UserRole


class UserCreate(UserBase):
    """Corps de POST — champs communs plus le mot de passe en clair (min 8)."""

    password: str = Field(min_length=8)


class UserRead(UserBase):
    """Réponse API — jamais de champ mot de passe, en clair ou haché."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Corps de PATCH — tous champs optionnels, sémantique ``exclude_unset``."""

    email: EmailStr | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
