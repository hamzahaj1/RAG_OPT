# [FILE] — app/domains/projects/models.py
# [MODEL]
# synthesis: A Project is referenced by tasks.project_id (CASCADE — cascade-deleted).
# entity: Project
# table: projects
# columns: created_at, description, id, name, organization_id, updated_at
# fks: organization_id -> organizations.id [RESTRICT]
# referenced_by: tasks.project_id -> CASCADE
# [/MODEL]
"""SQLAlchemy model of the projects domain.

Central domain of the platform: ``organization_id`` references
``organizations.id`` with ``ondelete=RESTRICT`` — the DB refuses to
delete an occupied organization, as the backstop of the
application-level 409 (D2). The cascade direction goes down from
projects to tasks then comments (Milestones 7–8); never the reverse. No
cross-domain ORM navigation (no ``relationship()`` in Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class Project(Base):
    """Project attached to an organization.

    Invariants:
    - ``name`` is unique **within its organization** (composite
      constraint ``(organization_id, name)``, D14) — two organizations
      may hold same-named projects;
    - ``organization_id`` always points to an existing organization:
      checked by the service (404 on write) and by the ``RESTRICT`` FK
      (D2); the organization is not modifiable in Phase 2;
    - ``description`` is never NULL: empty string by default.
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
