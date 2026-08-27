# [FILE] — app/domains/tasks/schemas.py
# [SCHEMA]
# domain: tasks
# schemas: TaskBase(BaseModel), TaskCreate(TaskBase), TaskRead(TaskBase), TaskUpdate(BaseModel)
# entity: Task
# [/SCHEMA]
"""Schémas Pydantic du domaine tasks.

Données pures, sans logique ni méthode : quatre classes (Base, Create,
Read, Update) en ordre alphabétique. ``project_id`` n'apparaît que sur
Create et Read — le projet n'est pas modifiable en Phase 2 ; ``assignee_id``
est le seul parent modifiable de la phase : présent sur Update, où un
``null`` explicite désassigne tandis qu'un champ absent ne change rien
(sémantique ``exclude_unset``). Les longueurs maximales sont alignées sur
les colonnes de ``models.py``.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.tasks.models import TaskPriority, TaskStatus

# ──────────────

# [CODE_START]


class TaskBase(BaseModel):
    """Champs communs aux écritures et aux lectures d'une tâche."""

    description: str = ""
    priority: TaskPriority
    status: TaskStatus
    title: str = Field(max_length=200)


class TaskCreate(TaskBase):
    """Corps de POST — champs communs plus le projet (fixé) et l'assigné optionnel."""

    assignee_id: int | None = None
    project_id: int


class TaskRead(TaskBase):
    """Réponse API — état complet, projet, assigné éventuel et horodatages."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assignee_id: int | None
    project_id: int
    created_at: datetime
    updated_at: datetime


class TaskUpdate(BaseModel):
    """Corps de PATCH — tous champs optionnels, sémantique ``exclude_unset``.

    ``assignee_id`` distingue trois cas : champ absent (pas de
    changement), ``null`` explicite (désassignation), entier (assignation).
    """

    assignee_id: int | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    title: str | None = Field(default=None, max_length=200)
