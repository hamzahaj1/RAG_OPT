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
"""SQLAlchemy model of the users domain.

Relational bedrock of the platform: organizations (owner), tasks
(assignee) and comments (author) reference ``users.id`` through
explicit FKs — no cross-domain ORM navigation (no ``relationship()``
in Phase 2).
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
    """Closed set of user roles — persisted as ``String`` + CHECK (D1)."""

    ADMIN = "admin"
    MEMBER = "member"


class User(Base):
    """User account of the platform.

    Invariants:
    - ``email`` is unique across the whole platform (unique index);
    - ``hashed_password`` never contains a cleartext password and is
      exposed by no response schema;
    - ``role`` is bounded to the ``UserRole`` set by a named CHECK.
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
