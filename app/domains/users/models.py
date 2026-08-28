# [FILE] — app/domains/users/models.py
# [MODEL]
# synthesis: A User is referenced by comments.author_id (RESTRICT — blocked),
#   organizations.owner_id (RESTRICT — blocked), tasks.assignee_id (SET NULL — unassigned).
# entity: User
# table: users
# columns: created_at, email, full_name, hashed_password, id, role, updated_at
# fks: none
# referenced_by: comments.author_id -> RESTRICT, organizations.owner_id -> RESTRICT,
#   tasks.assignee_id -> SET NULL
# [/MODEL]
"""Modèle SQLAlchemy du domaine users.

Socle relationnel de la plateforme : les organisations (propriétaire),
les tâches (assigné) et les commentaires (auteur) référencent ``users.id``
par FK explicite — aucune navigation ORM inter-domaines (pas de
``relationship()`` en Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class UserRole(str, Enum):
    """Ensemble fermé des rôles utilisateur — persisté en ``String`` + CHECK (D1)."""

    ADMIN = "admin"
    MEMBER = "member"


class User(Base):
    """Compte utilisateur de la plateforme.

    Invariants :
    - ``email`` est unique sur toute la plateforme (index unique) ;
    - ``hashed_password`` ne contient jamais un mot de passe en clair et
      n'est exposé par aucun schéma de réponse ;
    - ``role`` est borné au périmètre de ``UserRole`` par CHECK nommé.
    """

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'member')", name="role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), server_default=UserRole.MEMBER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
