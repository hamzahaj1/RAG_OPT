# [FILE] — app/domains/comments/schemas.py
"""Schémas Pydantic du domaine comments.

Données pures, sans logique ni méthode : quatre classes (Base, Create,
Read, Update) en ordre alphabétique. ``author_id`` et ``task_id``
n'apparaissent que sur Create et Read — ni la tâche ni l'auteur ne sont
modifiables en Phase 2 : Update ne porte que ``content``. ``content`` est
un ``Text`` sans borne de longueur, aligné sur la colonne de ``models.py``.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ──────────────

# [CODE_START]


class CommentBase(BaseModel):
    """Champs communs aux écritures et aux lectures d'un commentaire."""

    content: str


class CommentCreate(CommentBase):
    """Corps de POST — champs communs plus la tâche et l'auteur (fixés)."""

    author_id: int
    task_id: int


class CommentRead(CommentBase):
    """Réponse API — état complet, tâche, auteur et horodatages."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int
    task_id: int
    created_at: datetime
    updated_at: datetime


class CommentUpdate(BaseModel):
    """Corps de PATCH — seul ``content`` est modifiable, sémantique ``exclude_unset``."""

    content: str | None = None
