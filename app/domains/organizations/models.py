# [FILE] — app/domains/organizations/models.py
# [MODEL]
# synthese: Un Organization est référencé par projects.organization_id (RESTRICT — blocage).
# entity: Organization
# table: organizations
# columns: created_at, id, name, owner_id, updated_at
# fks: owner_id -> users.id [RESTRICT]
# referenced_by: projects.organization_id -> RESTRICT
# [/MODEL]
"""Modèle SQLAlchemy du domaine organizations.

Première relation inter-domaines du projet : ``owner_id`` référence
``users.id`` en ``ondelete=RESTRICT`` — la DB refuse la suppression d'un
propriétaire, en backstop du 409 applicatif (D2). Aucune navigation ORM
inter-domaines (pas de ``relationship()`` en Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class Organization(Base):
    """Organisation propriétaire de projets.

    Invariants :
    - ``name`` est unique sur toute la plateforme (contrainte unique) ;
    - ``owner_id`` pointe toujours vers un utilisateur existant : vérifié
      par le service (404 à l'écriture) et par la FK ``RESTRICT`` (D2) ;
    - le propriétaire n'est pas modifiable en Phase 2 (absent des Update).
    """

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
