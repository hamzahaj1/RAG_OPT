# [FILE] — app/domains/projects/models.py
# [MODEL]
# synthese: Un Project est référencé par tasks.project_id (CASCADE — suppression en cascade).
# entity: Project
# table: projects
# columns: created_at, description, id, name, organization_id, updated_at
# fks: organization_id -> organizations.id [RESTRICT]
# referenced_by: tasks.project_id -> CASCADE
# [/MODEL]
"""Modèle SQLAlchemy du domaine projects.

Domaine central de la plateforme : ``organization_id`` référence
``organizations.id`` en ``ondelete=RESTRICT`` — la DB refuse la
suppression d'une organisation occupée, en backstop du 409 applicatif
(D2). Le sens de la cascade descend de projects vers tasks puis comments
(Jalons 7–8) ; jamais l'inverse. Aucune navigation ORM inter-domaines
(pas de ``relationship()`` en Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class Project(Base):
    """Projet rattaché à une organisation.

    Invariants :
    - ``name`` est unique **au sein de son organisation** (contrainte
      composée ``(organization_id, name)``, D14) — deux organisations
      peuvent porter des projets homonymes ;
    - ``organization_id`` pointe toujours vers une organisation
      existante : vérifié par le service (404 à l'écriture) et par la FK
      ``RESTRICT`` (D2) ; l'organisation n'est pas modifiable en Phase 2 ;
    - ``description`` n'est jamais NULL : chaîne vide par défaut.
    """

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(Text, server_default="")
    name: Mapped[str] = mapped_column(String(100))
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
