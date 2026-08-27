# [FILE] — app/domains/organizations/schemas.py
"""Schémas Pydantic du domaine organizations.

Données pures, sans logique ni méthode : quatre classes (Base, Create,
Read, Update) en ordre alphabétique. ``owner_id`` n'apparaît que sur
Create et Read — le propriétaire n'est pas modifiable en Phase 2 ; les
longueurs maximales sont alignées sur les colonnes de ``models.py``.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ──────────────

# [CODE_START]


class OrganizationBase(BaseModel):
    """Champs communs aux écritures et aux lectures d'une organisation."""

    name: str = Field(max_length=100)


class OrganizationCreate(OrganizationBase):
    """Corps de POST — champs communs plus le propriétaire, fixé à la création."""

    owner_id: int


class OrganizationRead(OrganizationBase):
    """Réponse API — état complet, propriétaire et horodatages inclus."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class OrganizationUpdate(BaseModel):
    """Corps de PATCH — seul ``name`` est modifiable, sémantique ``exclude_unset``."""

    name: str | None = Field(default=None, max_length=100)
