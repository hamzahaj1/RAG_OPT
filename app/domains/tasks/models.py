# [FILE] — app/domains/tasks/models.py
"""Modèle SQLAlchemy du domaine tasks.

Premier domaine à double référence inter-domaines : ``project_id``
référence ``projects.id`` en ``ondelete=CASCADE`` (la suppression d'un
projet emporte ses tâches — axe de contenance, DB seule) ; ``assignee_id``
référence ``users.id`` en ``ondelete=SET NULL`` (la suppression d'un
utilisateur désassigne ses tâches sans les détruire — DB seule, D2).
Aucune navigation ORM inter-domaines (pas de ``relationship()`` en
Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class TaskPriority(str, Enum):
    """Ensemble fermé des priorités de tâche — persisté en ``String`` + CHECK (D1)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    """Ensemble fermé des statuts de tâche — persisté en ``String`` + CHECK (D1)."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(Base):
    """Tâche rattachée à un projet, assignable à un utilisateur.

    Invariants :
    - ``project_id`` pointe toujours vers un projet existant : vérifié
      par le service (404 à l'écriture) et par la FK ``CASCADE`` — la
      suppression du projet emporte la tâche (jamais l'inverse) ;
    - ``assignee_id`` est la seule FK nullable de la phase : ``NULL``
      signifie « non assignée » ; la suppression de l'assigné remet
      ``NULL`` par la DB seule (``SET NULL``, D2) ;
    - ``status`` et ``priority`` sont bornés à leurs enums par CHECK
      nommés ; ``description`` n'est jamais NULL (chaîne vide par défaut).
    """

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="priority"),
        CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    description: Mapped[str] = mapped_column(Text, server_default="")
    priority: Mapped[str] = mapped_column(String(20), server_default=TaskPriority.MEDIUM.value)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), server_default=TaskStatus.TODO.value)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
