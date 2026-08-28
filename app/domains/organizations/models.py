# [FILE] — app/domains/organizations/models.py
# [MODEL]
# synthesis: A Organization is referenced by projects.organization_id (RESTRICT — blocked).
# entity: Organization
# table: organizations
# columns: created_at, id, name, owner_id, updated_at
# fks: owner_id -> users.id [RESTRICT]
# referenced_by: projects.organization_id -> RESTRICT
# [/MODEL]
"""SQLAlchemy model of the organizations domain.

First cross-domain relation of the project: ``owner_id`` references
``users.id`` with ``ondelete=RESTRICT`` — the DB refuses to delete an
owner, as the backstop of the application-level 409 (D2). No
cross-domain ORM navigation (no ``relationship()`` in Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class Organization(Base):
    """Organization owning projects.

    Invariants:
    - ``name`` is unique across the whole platform (unique constraint);
    - ``owner_id`` always points to an existing user: checked by the
      service (404 on write) and by the ``RESTRICT`` FK (D2);
    - the owner is not modifiable in Phase 2 (absent from Update).
    """

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
