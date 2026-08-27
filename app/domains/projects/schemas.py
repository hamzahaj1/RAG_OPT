# [FILE] — app/domains/projects/schemas.py
# [SCHEMA]
# domain: projects
# schemas: ProjectBase(BaseModel), ProjectCreate(ProjectBase), ProjectRead(ProjectBase),
#   ProjectUpdate(BaseModel)
# entity: Project
# [/SCHEMA]
"""Schémas Pydantic du domaine projects.

Données pures, sans logique ni méthode : quatre classes (Base, Create,
Read, Update) en ordre alphabétique. ``organization_id`` n'apparaît que
sur Create et Read — l'organisation n'est pas modifiable en Phase 2 ;
``description`` porte le même défaut chaîne vide que la colonne ; les
longueurs maximales sont alignées sur les colonnes de ``models.py``.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ──────────────

# [CODE_START]


class ProjectBase(BaseModel):
    """Champs communs aux écritures et aux lectures d'un projet."""

    description: str = ""
    name: str = Field(max_length=100)


class ProjectCreate(ProjectBase):
    """Corps de POST — champs communs plus l'organisation, fixée à la création."""

    organization_id: int


class ProjectRead(ProjectBase):
    """Réponse API — état complet, organisation et horodatages inclus."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime


class ProjectUpdate(BaseModel):
    """Corps de PATCH — nom et description seuls, sémantique ``exclude_unset``."""

    description: str | None = None
    name: str | None = Field(default=None, max_length=100)
